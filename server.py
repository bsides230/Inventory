import io
import os
import re
import json
import logging
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import jwt
import pandas as pd
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from auth import AuthenticatedUser, get_optional_authenticated_user, get_required_authenticated_user
from services.email_delivery import OrderEmailDeliveryService, SmtpEmailClient
from file_safety import write_json_atomic, append_jsonl, with_lock
from services.draft_manager import FileDraftManager
from services.order_manager import FileOrderManager
from services.recipients import RecipientConfigError, RecipientConfigStore
from update_inventory_data import check_and_update, convert_excel_to_json


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    app_version: str = "0.1.0"
    database_url: str = "sqlite:///./inventory.db"
    auth_jwt_secret: str = "change-me"
    auth_jwt_algorithm: str = "HS256"
    order_recipients_file: str = "config/order_recipients.txt"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False
    smtp_sender_email: str = "inventory@example.com"
    email_retry_attempts: int = 3
    email_retry_delay_seconds: float = 0.1
    email_dead_letter_log: str = "logs/order_email_dead_letter.log"
    cors_allowed_origins: str = "*"
    max_request_body_bytes: int = 1048576
    rate_limit_max_requests: int = 120
    rate_limit_window_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(record, "request_id", "-")
        return True


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [request_id=%(request_id)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, key: str, now: float | None = None) -> bool:
        current = now if now is not None else time.time()
        window_start = current - self.window_seconds
        request_times = self._requests.get(key, [])
        filtered = [ts for ts in request_times if ts >= window_start]
        if len(filtered) >= self.max_requests:
            self._requests[key] = filtered
            return False
        filtered.append(current)
        self._requests[key] = filtered
        return True


# --- File paths ---
LOCATION_FILE = Path("location.txt")
CATEGORIES_FILE = Path("categories.json")
DATA_DIR = Path("data")
ITEM_MASTER_DIR = Path("item master")
ORDERS_DIR = Path("orders")
LOGS_DIR = Path("logs")
LOCATIONS_CONFIG = Path("config/locations.txt")
ADMIN_PASSWORD_FILE = Path("config/admin_password.txt")
EMAIL_SETTINGS_FILE = Path("config/email_settings.txt")
RECIPIENTS_FILE = Path("config/order_recipients.txt")
CATEGORY_ORDER_FILE = Path("config/category_order.json")
UI_LABELS_FILE = Path("config/ui_labels.json")
BRANDING_FILE = Path("config/branding.json")
APP_SETTINGS_FILE = Path("config/app_settings.json")


def load_app_settings() -> dict:
    defaults = {"output_language": "en"}
    if APP_SETTINGS_FILE.exists():
        try:
            with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_app_settings(settings: dict):
    APP_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)


# --- Config helpers ---
def load_locations() -> dict[str, str]:
    """Load PIN->LocationName mapping from locations.txt"""
    result = {}
    if not LOCATIONS_CONFIG.exists():
        return result
    with open(LOCATIONS_CONFIG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 1)
            if len(parts) == 2:
                pin, name = parts[0].strip(), parts[1].strip()
                if pin.isdigit() and len(pin) == 4:
                    result[pin] = name
    return result


def save_locations(locations: dict[str, str]) -> None:
    """Save PIN->LocationName mapping to locations.txt"""
    lines = [
        "# Location PIN mappings",
        "# Format: PIN|Location Name  (PIN must be exactly 4 digits)",
        "# Lines starting with # are comments and are ignored.",
    ]
    for pin, name in sorted(locations.items()):
        lines.append(f"{pin}|{name}")
    LOCATIONS_CONFIG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_admin_password() -> str:
    if ADMIN_PASSWORD_FILE.exists():
        return ADMIN_PASSWORD_FILE.read_text(encoding="utf-8").strip()
    return "admin"


def load_email_settings() -> dict:
    defaults = {
        "smtp_host": "localhost",
        "smtp_port": "1025",
        "smtp_username": "",
        "smtp_password": "",
        "smtp_use_tls": "false",
        "smtp_sender_email": "inventory@example.com",
    }
    if not EMAIL_SETTINGS_FILE.exists():
        return defaults
    with open(EMAIL_SETTINGS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                defaults[k.strip()] = v.strip()
    return defaults


def save_email_settings(s: dict) -> None:
    lines = []
    for k, v in s.items():
        lines.append(f"{k}={v}")
    EMAIL_SETTINGS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_email_service():
    """Build email delivery service from config file (called fresh for each order)."""
    es = load_email_settings()
    smtp_client = SmtpEmailClient(
        host=es["smtp_host"],
        port=int(es.get("smtp_port", 1025)),
        username=es.get("smtp_username") or None,
        password=es.get("smtp_password") or None,
        use_tls=es.get("smtp_use_tls", "false").lower() == "true",
    )
    recipient_store = RecipientConfigStore(RECIPIENTS_FILE)
    try:
        recipient_store.get_recipients()
        return OrderEmailDeliveryService(
            recipient_store=recipient_store,
            smtp_client=smtp_client,
            sender_email=es.get("smtp_sender_email", "inventory@example.com"),
            max_attempts=settings.email_retry_attempts,
            retry_delay_seconds=settings.email_retry_delay_seconds,
            dead_letter_log_path=Path(settings.email_dead_letter_log),
        )
    except RecipientConfigError as exc:
        logger.error("Recipient config invalid: %s", exc)
        return NullOrderEmailDeliveryService(error=str(exc))


def load_recipients() -> list[str]:
    if not RECIPIENTS_FILE.exists():
        return []
    lines = []
    with open(RECIPIENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def save_recipients(recipients: list[str]) -> None:
    lines = ["# Order recipient emails (one per line)"] + recipients
    RECIPIENTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


@dataclass
class NullOrderEmailDeliveryService:
    error: str

    def send_order_email(self, **kwargs):
        from services.email_delivery import EmailDeliveryResult
        return EmailDeliveryResult(status="failed", attempts=0, error=self.error)


def get_location_name():
    if LOCATION_FILE.exists():
        with open(LOCATION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Falcones Pizza"


app = FastAPI(title=f"{get_location_name()} Inventory")
app.state.settings = settings
app.state.rate_limiter = InMemoryRateLimiter(
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

WEB_DIR = Path("web")
FLAGS_DIR = Path("global_flags")
DRAFTS_DIR = Path("drafts")
WEB_DIR.mkdir(exist_ok=True)
FLAGS_DIR.mkdir(exist_ok=True)
ITEM_MASTER_DIR.mkdir(exist_ok=True)
ORDERS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
DRAFTS_DIR.mkdir(exist_ok=True)

check_and_update()


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    logger.info("Request started %s %s", request.method, request.url.path, extra={"request_id": request_id})
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info("Request completed %s %s status=%s", request.method, request.url.path, response.status_code, extra={"request_id": request_id})
    return response


@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith(('.html', '.js', '.css')) or path in ('/', '/admin'):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.middleware("http")
async def security_guard_middleware(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.max_request_body_bytes:
                    return JSONResponse(status_code=413, content={"detail": "Request body too large"})
            except ValueError:
                logger.warning("Invalid content-length header: %s", content_length)

    client_host = request.client.host if request.client else "unknown"
    if not app.state.rate_limiter.is_allowed(client_host):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return await call_next(request)


def _cors_origins_from_settings() -> list[str]:
    origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    if "*" in origins:
        return ["*"]
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_from_settings(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


_admin_bearer = HTTPBearer(auto_error=False)


# --- Admin auth dependency ---
def get_required_admin(credentials: HTTPAuthorizationCredentials | None = Depends(_admin_bearer)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.auth_jwt_secret, algorithms=[settings.auth_jwt_algorithm])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid admin token")


# --- Data Loading ---
def load_categories_config() -> Dict[str, dict]:
    if CATEGORIES_FILE.exists():
        with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_categories_config(config: Dict[str, dict]):
    with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def get_inventory_category(category: str):
    check_and_update()
    cat_file = DATA_DIR / f"{category}.json"
    if cat_file.exists():
        try:
            with open(cat_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Error reading %s.json: %s", category, exc, exc_info=True)
            return None
    return None


def get_all_inventory_categories():
    check_and_update()
    categories = []
    if DATA_DIR.exists():
        for file in DATA_DIR.glob("*.json"):
            categories.append(file.stem)

    # Sort categories based on config/category_order.json if it exists
    if CATEGORY_ORDER_FILE.exists():
        try:
            with open(CATEGORY_ORDER_FILE, "r", encoding="utf-8") as f:
                order_data = json.load(f)
                order_list = order_data.get("order", [])

                # Create a lookup for defined order
                order_map = {cat_id: idx for idx, cat_id in enumerate(order_list)}

                # Sort: items in order_list first (by their index), then others alphabetically
                categories.sort(key=lambda x: (order_map.get(x, 999999), x))
        except Exception as exc:
            logger.error("Error reading category_order.json: %s", exc, exc_info=True)
            categories.sort()
    else:
        categories.sort()

    return categories


def _build_item_lookup(category_data: dict) -> dict[str, dict]:
    return {item["id"]: item for item in category_data.get("items", [])}


# --- Models ---
class PinAuthRequest(BaseModel):
    pin: str


class AdminLoginRequest(BaseModel):
    password: str


class UpdateItemRequest(BaseModel):
    id: str
    qty: int
    unit: str
    version: Optional[int] = None


class SubmitOrderRequest(BaseModel):
    date: str
    is_rush: bool
    needed_by: Optional[str] = None
    draft_id: Optional[int] = None
    save_only: bool = False


class NewDraftRequest(BaseModel):
    name: Optional[str] = None


class RenameDraftRequest(BaseModel):
    name: str


class AddLocationRequest(BaseModel):
    pin: str
    name: str


class UpdateEmailSettingsRequest(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = False
    smtp_sender_email: str


class UpdateRecipientsRequest(BaseModel):
    recipients: List[str]


class UpdateAdminPasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateCategoryOrderRequest(BaseModel):
    order: List[str]


class UpdateUILabelsRequest(BaseModel):
    labels: Dict[str, str]


class UpdateBrandingRequest(BaseModel):
    branding: Dict[str, str]


# --- Auth Endpoints ---
@app.post("/api/auth/pin")
async def auth_pin(body: PinAuthRequest):
    pin = body.pin.strip()
    if not pin.isdigit() or len(pin) != 4:
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")

    locations = load_locations()
    if pin not in locations:
        raise HTTPException(status_code=401, detail="Invalid PIN")

    location_name = locations[pin]

    # Create a unique session id
    timestamp = int(time.time())
    nonce = uuid.uuid4().hex[:8]
    session_id = f"pin_{pin}_{timestamp}_{nonce}"

    payload = {
        "sub": session_id,
        "external_id": f"pin_{pin}",
        "location_pin": pin,
        "location_name": location_name,
        "name": location_name,
        "email": f"pin_{pin}@location.local",
        "role": "user",
    }
    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)
    return {"token": token, "location_name": location_name, "pin": pin}


@app.post("/api/admin/login")
async def admin_login(body: AdminLoginRequest):
    expected = get_admin_password()
    if body.password != expected:
        raise HTTPException(status_code=401, detail="Invalid admin password")
    payload = {"sub": "admin", "role": "admin"}
    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)
    return {"token": token}


# --- Health ---
@app.get("/health/live")
async def health_live():
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready():
    checks = {
        "data_dir": DATA_DIR.exists() and os.access(DATA_DIR, os.R_OK),
        "categories_file": CATEGORIES_FILE.exists() and os.access(CATEGORIES_FILE, os.R_OK),
        "orders_dir_writable": ORDERS_DIR.exists() and os.access(ORDERS_DIR, os.W_OK),
        "drafts_dir_writable": DRAFTS_DIR.exists() and os.access(DRAFTS_DIR, os.W_OK),
        "ipc_dir_writable": Path("ipc/inbox").exists() and os.access(Path("ipc/inbox"), os.W_OK),
    }
    status = "ready" if all(checks.values()) else "not_ready"
    return {"status": status, "checks": checks}

@app.get("/health/queue")
async def health_queue():
    inbox = len(list(Path("ipc/inbox").glob("*.json"))) if Path("ipc/inbox").exists() else 0
    processing = len(list(Path("ipc/processing").glob("*.json"))) if Path("ipc/processing").exists() else 0
    failed = len(list(Path("ipc/failed").glob("*.json"))) if Path("ipc/failed").exists() else 0
    return {
        "status": "ok",
        "counts": {
            "inbox": inbox,
            "processing": processing,
            "failed": failed
        }
    }


@app.get("/api/version")
async def get_version():
    return {"version": settings.app_version, "environment": settings.app_env}


@app.get("/api/status")
async def get_status():
    return {"status": "online", "location": get_location_name()}


@app.get("/api/branding")
async def get_branding():
    branding = {}
    if BRANDING_FILE.exists():
        try:
            with open(BRANDING_FILE, "r", encoding="utf-8") as f:
                branding = json.load(f)
        except Exception as exc:
            logger.error("Error reading branding.json: %s", exc, exc_info=True)
    return {"success": True, "branding": branding}


@app.get("/api/ui-labels")
async def get_ui_labels():
    labels = {}
    if UI_LABELS_FILE.exists():
        try:
            with open(UI_LABELS_FILE, "r", encoding="utf-8") as f:
                labels = json.load(f)
        except Exception as exc:
            logger.error("Error reading ui_labels.json: %s", exc, exc_info=True)
    return {"success": True, "labels": labels}


@app.get("/api/categories")
async def get_categories():
    cat_ids = get_all_inventory_categories()
    config = load_categories_config()
    categories = []
    for cat_id in cat_ids:
        cat_data = get_inventory_category(cat_id)
        if cat_data:
            cat_config = config.get(cat_id, {})
            cat_obj = {
                "id": cat_id,
                "icon": cat_config.get("icon", "box"),
                "color": cat_config.get("color", "gray"),
            }
            for k, v in cat_config.items():
                if k.startswith("label_"):
                    cat_obj[k] = v
            if "label_en" not in cat_obj:
                cat_obj["label_en"] = cat_config.get("label", cat_data.get("label", cat_id))
            categories.append(cat_obj)
    return {"success": True, "categories": categories}


@app.get("/api/inventory/{category}")
async def get_inventory(
    category: str,
    draft_id: Optional[int] = Query(None),
    user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
):
    category_lower = category.lower()
    cat_data = get_inventory_category(category_lower)

    if cat_data:
        items = cat_data["items"]
        draft_quantities: dict[str, tuple[int, str]] = {}
        item_frequencies: dict[str, int] = {}
        if user:
            draft_manager = FileDraftManager(DRAFTS_DIR)
            order_manager = FileOrderManager(ORDERS_DIR)

            if draft_id:
                draft = draft_manager.get_draft(user.external_id, draft_id)
            else:
                draft = draft_manager.get_active_draft(user.external_id)

            if draft:
                draft_quantities = {item["item_id"]: (item["quantity"], item["unit"]) for item in draft.get("items", [])}

            user_frequencies = order_manager.get_item_frequencies(user.external_id)
            item_frequencies = user_frequencies.get(user.external_id, {})

        response_items = []
        for item in items:
            quantity, unit = draft_quantities.get(item["id"], (0, "each"))
            response_items.append({**item, "qty": quantity, "unit": unit})

        if user:
            response_items.sort(key=lambda x: item_frequencies.get(x["id"], 0), reverse=True)

        return {"success": True, "items": response_items}

    return {"success": True, "items": []}


@app.post("/api/inventory/{category}/update")
async def update_inventory(
    category: str,
    request: UpdateItemRequest,
    draft_id: Optional[int] = Query(None),
    user: AuthenticatedUser = Depends(get_required_authenticated_user),
):
    category_lower = category.lower()
    cat_data = get_inventory_category(category_lower)
    if not cat_data:
        raise HTTPException(status_code=404, detail="Category not found")

    item_lookup = _build_item_lookup(cat_data)
    target_item = item_lookup.get(request.id)
    if not target_item:
        raise HTTPException(status_code=404, detail="Item not found in category")

    draft_manager = FileDraftManager(DRAFTS_DIR)

    if draft_id:
        draft = draft_manager.get_draft(user.external_id, draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Draft not found")
    else:
        draft = draft_manager.get_active_draft(user.external_id)
        if not draft:
            draft = draft_manager.create_draft(user.external_id)
            draft_id = int(draft["id"])

    # Update items
    items = draft.get("items", [])
    item_idx = next((i for i, v in enumerate(items) if v["item_id"] == request.id), None)

    if request.qty <= 0:
        if item_idx is not None:
            items.pop(item_idx)
    else:
        new_item = {
            "item_id": request.id,
            "category_id": category_lower,
            "item_name": target_item.get("name_en", target_item.get("name", request.id)),
            "item_name_es": target_item.get("name_es", ""),
            "quantity": request.qty,
            "unit": request.unit,
        }
        if item_idx is not None:
            items[item_idx] = new_item
        else:
            items.append(new_item)

    try:
        draft_manager.update_draft(
            user.external_id,
            int(draft["id"]),
            items=items,
            expected_version=request.version
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"success": True}


# --- Draft Management Endpoints ---
@app.get("/api/drafts")
async def list_drafts(user: AuthenticatedUser = Depends(get_required_authenticated_user)):
    draft_manager = FileDraftManager(DRAFTS_DIR)
    all_drafts = draft_manager.get_all_active_drafts(user.external_id)
    result = []
    for d in all_drafts:
        result.append({
            "id": int(d["id"]),
            "name": d.get("draft_name", f"Draft {d['id']}"),
            "item_count": len(d.get("items", [])),
            "updated_at": d.get("updated_at"),
            "created_at": d.get("created_at"),
        })
    return {"success": True, "drafts": result}


@app.post("/api/drafts/new")
async def create_draft(body: NewDraftRequest, user: AuthenticatedUser = Depends(get_required_authenticated_user)):
    draft_manager = FileDraftManager(DRAFTS_DIR)

    # Safe filename validation for draft name if provided
    name = body.name
    if name:
        if not re.match(r"^[A-Za-z0-9\s\-_]+$", name):
            raise HTTPException(status_code=400, detail="Invalid characters in draft name")

    draft = draft_manager.create_draft(user.external_id, name=name)
    return {"success": True, "draft": {"id": int(draft["id"]), "name": draft["draft_name"], "item_count": 0}}


@app.post("/api/drafts/{draft_id}/rename")
async def rename_draft(
    draft_id: int,
    body: RenameDraftRequest,
    user: AuthenticatedUser = Depends(get_required_authenticated_user),
):
    draft_manager = FileDraftManager(DRAFTS_DIR)

    # Safe filename validation for draft name
    name = body.name
    if not re.match(r"^[A-Za-z0-9\s\-_]+$", name):
        raise HTTPException(status_code=400, detail="Invalid characters in draft name")

    draft = draft_manager.update_draft(user.external_id, draft_id, name=name)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True}


@app.delete("/api/drafts/{draft_id}")
async def delete_draft(draft_id: int, user: AuthenticatedUser = Depends(get_required_authenticated_user)):
    draft_manager = FileDraftManager(DRAFTS_DIR)
    deleted = draft_manager.delete_draft(user.external_id, draft_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True}


@app.post("/api/submit_order")
async def submit_order(
    request: SubmitOrderRequest,
    user: AuthenticatedUser = Depends(get_required_authenticated_user),
):
    location = get_location_name().replace("/", "_").replace("\\", "_")
    location_pin = getattr(user, "external_id", "").replace("pin_", "") if user.external_id.startswith("pin_") else None
    location_name = user.display_name

    if request.save_only:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"order_{ts}.xlsx"
        saved_dir = ORDERS_DIR / "saved"
        saved_dir.mkdir(parents=True, exist_ok=True)
        filepath = saved_dir / filename
    else:
        if request.is_rush and request.needed_by:
            filename = f"{location} URGENT ORDER by {request.needed_by}.xlsx"
        else:
            date_str = request.date.replace("/", "-")
            filename = f"{location} Falcones Order {date_str}.xlsx"
        filepath = ORDERS_DIR / filename

    try:
        draft_manager = FileDraftManager(DRAFTS_DIR)
        order_manager = FileOrderManager(ORDERS_DIR)

        if request.draft_id:
            draft = draft_manager.get_draft(user.external_id, request.draft_id)
        else:
            draft = draft_manager.get_active_draft(user.external_id)

        if draft is None or not draft.get("items"):
            return {"success": False, "message": "No items to order."}

        draft["is_rush"] = request.is_rush
        draft["needed_by"] = request.needed_by
        draft_items = draft.get("items", [])

        app_settings = load_app_settings()
        output_lang = app_settings.get("output_language", "en")

        items_by_category = {}
        for draft_item in draft_items:
            category_data = get_inventory_category(draft_item["category_id"])
            category_label = category_data["label"] if category_data else draft_item["category_id"]
            if output_lang == "es" and category_data:
                category_label = category_data.get("label_es", category_label)
            item_name = draft_item.get("item_name", "")
            if output_lang == "es":
                item_name = draft_item.get("item_name_es") or draft_item.get("item_name", "")
            items_by_category.setdefault(category_label, []).append({
                "Item": item_name,
                "Quantity": draft_item["quantity"],
                "Unit": draft_item["unit"],
            })

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            for cat_label in sorted(items_by_category.keys()):
                cat_items = items_by_category[cat_label]
                df = pd.DataFrame(cat_items)
                safe_sheet = re.sub(r'[\[\]:*?/\\]', '', cat_label)[:31] or "Sheet"
                df.to_excel(writer, sheet_name=safe_sheet, index=False)

        if request.save_only:
            logger.info(
                "Order saved only location_pin=%s location_name=%s file=%s",
                location_pin, location_name, filepath,
            )
            return {
                "success": True,
                "message": "Order saved successfully",
                "filename": filename,
                "delivery_status": "skipped",
                "delivery_attempts": 0,
                "delivery_error": None,
            }

        order = order_manager.create_order(
            user.external_id,
            draft,
            export_filename=filename,
            location_pin=location_pin,
            location_name=location_name,
        )

        # Write orders/flags/<order_id>.state as submitted
        flags_dir = ORDERS_DIR / "flags"
        flags_dir.mkdir(parents=True, exist_ok=True)
        flag_path = flags_dir / f"{order['id']}.state"
        flag_path.write_text("submitted", encoding="utf-8")

        # update draft state
        draft_manager.update_draft(user.external_id, int(draft["id"]), state="submitted")

        # enqueue ipc event
        event_id = str(uuid.uuid4())
        event_payload = {
            "event_id": event_id,
            "event_type": "email_send",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "order_id": order["id"],
                "location": location_name or location,
                "date": request.date,
                "is_rush": request.is_rush,
                "needed_by": request.needed_by,
                "export_path": str(filepath)
            }
        }

        ipc_inbox_dir = Path("ipc/inbox")
        ipc_inbox_dir.mkdir(parents=True, exist_ok=True)
        event_path = ipc_inbox_dir / f"{event_id}.json"

        from file_safety import write_json_atomic
        write_json_atomic(event_path, event_payload)

        # set initial delivery status to pending
        delivery_status = "pending"
        delivery_attempts = 0
        delivery_error = None

        logger.info(
            "Order submitted location_pin=%s location_name=%s file=%s delivery=%s event_id=%s",
            location_pin, location_name, filepath, delivery_status, event_id
        )
        return {
            "success": True,
            "message": "Order submitted successfully",
            "filename": filename,
            "delivery_status": delivery_status,
            "delivery_attempts": delivery_attempts,
            "delivery_error": delivery_error,
        }
    except Exception as exc:
        if filepath.exists():
            filepath.unlink()
        logger.error("Error saving order: %s", exc, exc_info=True)
        return {"success": False, "message": f"Error saving order: {str(exc)}"}


@app.get("/api/download/order/{filename:path}")
async def download_order_file(
    filename: str,
    user: AuthenticatedUser = Depends(get_required_authenticated_user),
):
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename:
        return JSONResponse(status_code=400, content={"detail": "Invalid filename"})
    filepath = ORDERS_DIR / safe_name
    if not filepath.exists():
        saved_path = ORDERS_DIR / "saved" / safe_name
        if saved_path.exists():
            filepath = saved_path
        else:
            return JSONResponse(status_code=404, content={"detail": "File not found"})
    resolved = filepath.resolve()
    if not str(resolved).startswith(str(ORDERS_DIR.resolve())):
        return JSONResponse(status_code=400, content={"detail": "Invalid filename"})
    return FileResponse(
        path=str(resolved),
        filename=safe_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# --- Admin Settings Endpoints ---
@app.get("/api/admin/settings")
async def admin_get_settings(_=Depends(get_required_admin)):
    return {"success": True, "settings": load_app_settings()}


@app.post("/api/admin/settings")
async def admin_save_settings(request: Request, _=Depends(get_required_admin)):
    body = await request.json()
    settings = load_app_settings()
    settings.update(body)
    save_app_settings(settings)
    return {"success": True}


@app.get("/api/admin/download-master")
async def admin_download_master(_=Depends(get_required_admin)):
    master_path = ITEM_MASTER_DIR / "Master.xlsx"
    if not master_path.exists():
        return JSONResponse(status_code=404, content={"detail": "No Master.xlsx found"})
    return FileResponse(
        path=str(master_path),
        filename="Master.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/admin/download-frequency-report")
async def admin_download_frequency_report(
    location_pin: str = "",
    _=Depends(get_required_admin),
):
    locations = load_locations()
    order_manager = FileOrderManager(ORDERS_DIR)
    frequencies = order_manager.get_item_frequencies()

    pin_frequencies = {}
    for user_id, freqs in frequencies.items():
        if user_id.startswith("pin_"):
            pin = user_id.replace("pin_", "")
            pin_frequencies[pin] = freqs

    cat_ids = get_all_inventory_categories()
    config = load_categories_config()

    location_name = "All Locations"
    if location_pin and location_pin in locations:
        location_name = locations[location_pin]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for cat_id in cat_ids:
            cat_data = get_inventory_category(cat_id)
            if not cat_data:
                continue
            cat_config = config.get(cat_id, {})
            cat_label = cat_config.get("label_en", cat_data.get("label", cat_id))
            items = cat_data.get("items", [])
            rows = []
            for item in items:
                freq = 0
                if location_pin:
                    freq = pin_frequencies.get(location_pin, {}).get(item["id"], 0)
                else:
                    for pin_freqs in pin_frequencies.values():
                        freq += pin_freqs.get(item["id"], 0)
                rows.append({"Item": item.get("name_en", item.get("name", "")), "Times Ordered": freq})
            if rows:
                df = pd.DataFrame(rows).sort_values(by="Times Ordered", ascending=False)
                safe_sheet = re.sub(r'[\[\]:*?/\\]', '', cat_label)[:31] or "Sheet"
                df.to_excel(writer, sheet_name=safe_sheet, index=False)

    output.seek(0)
    safe_loc = location_name.replace("/", "_").replace("\\", "_")
    report_filename = f"Frequency Report - {safe_loc}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{report_filename}"'},
    )


# --- Admin Endpoints ---
@app.get("/api/admin/aggregation")
async def admin_get_aggregation(_=Depends(get_required_admin)):
    locations = load_locations()
    order_manager = FileOrderManager(ORDERS_DIR)
    frequencies = order_manager.get_item_frequencies()

    # locations in response should be based on locations.txt config
    resp_locations = [{"pin": k, "name": v} for k, v in sorted(locations.items())]

    # frequencies map is currently user_id (which is f"pin_{pin}") -> item_id -> frequency
    # we need PIN -> item_id -> frequency
    pin_frequencies = {}
    for user_id, freqs in frequencies.items():
        if user_id.startswith("pin_"):
            pin = user_id.replace("pin_", "")
            pin_frequencies[pin] = freqs

    cat_ids = get_all_inventory_categories()
    config = load_categories_config()
    categories_data = []

    for cat_id in cat_ids:
        cat_data = get_inventory_category(cat_id)
        if cat_data:
            cat_config = config.get(cat_id, {})
            items = cat_data.get("items", [])
            categories_data.append({
                "id": cat_id,
                "label": cat_config.get("label_en", cat_config.get("label", cat_data["label"])),
                "items": [{"id": item["id"], "name": item["name_en"]} for item in items]
            })

    return {
        "success": True,
        "locations": resp_locations,
        "categories": categories_data,
        "frequencies": pin_frequencies
    }


@app.get("/api/admin/locations")
async def admin_get_locations(_=Depends(get_required_admin)):
    locations = load_locations()
    return {"success": True, "locations": [{"pin": k, "name": v} for k, v in sorted(locations.items())]}


@app.post("/api/admin/locations")
async def admin_add_location(body: AddLocationRequest, _=Depends(get_required_admin)):
    pin = body.pin.strip()
    if not pin.isdigit() or len(pin) != 4:
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Location name is required")
    locations = load_locations()
    locations[pin] = name
    save_locations(locations)
    return {"success": True}


@app.delete("/api/admin/locations/{pin}")
async def admin_delete_location(pin: str, _=Depends(get_required_admin)):
    locations = load_locations()
    if pin not in locations:
        raise HTTPException(status_code=404, detail="Location not found")
    del locations[pin]
    save_locations(locations)
    return {"success": True}


@app.get("/api/admin/email-settings")
async def admin_get_email_settings(_=Depends(get_required_admin)):
    es = load_email_settings()
    es_safe = {k: v for k, v in es.items() if k != "smtp_password"}
    es_safe["smtp_password"] = "***" if es.get("smtp_password") else ""
    return {"success": True, "settings": es_safe}


@app.post("/api/admin/email-settings")
async def admin_update_email_settings(body: UpdateEmailSettingsRequest, _=Depends(get_required_admin)):
    existing = load_email_settings()
    new_settings = {
        "smtp_host": body.smtp_host,
        "smtp_port": str(body.smtp_port),
        "smtp_username": body.smtp_username or "",
        "smtp_password": body.smtp_password if body.smtp_password and body.smtp_password != "***" else existing.get("smtp_password", ""),
        "smtp_use_tls": "true" if body.smtp_use_tls else "false",
        "smtp_sender_email": body.smtp_sender_email,
    }
    save_email_settings(new_settings)
    return {"success": True}


@app.get("/api/admin/recipients")
async def admin_get_recipients(_=Depends(get_required_admin)):
    recipients = load_recipients()
    return {"success": True, "recipients": recipients}


@app.post("/api/admin/recipients")
async def admin_update_recipients(body: UpdateRecipientsRequest, _=Depends(get_required_admin)):
    cleaned = [r.strip() for r in body.recipients if r.strip()]
    save_recipients(cleaned)
    return {"success": True}


@app.post("/api/admin/rebuild-inventory")
async def admin_rebuild_inventory(_=Depends(get_required_admin)):
    try:
        success = convert_excel_to_json()
        if success:
            return {"success": True, "message": "Inventory rebuilt successfully from Excel files."}
        else:
            return {"success": False, "message": "Rebuild failed. Check that Excel files exist in the 'item master' folder."}
    except Exception as exc:
        logger.error("Inventory rebuild error: %s", exc, exc_info=True)
        return {"success": False, "message": str(exc)}


@app.get("/api/admin/category-order")
async def admin_get_category_order(_=Depends(get_required_admin)):
    cat_ids = get_all_inventory_categories()
    config = load_categories_config()
    categories = []
    for cat_id in cat_ids:
        cat_data = get_inventory_category(cat_id)
        if cat_data:
            cat_config = config.get(cat_id, {})
            categories.append({
                "id": cat_id,
                "label_en": cat_config.get("label_en", cat_config.get("label", cat_data["label"])),
                "label_es": cat_config.get("label_es", cat_config.get("label", cat_data["label"])),
            })
    return {"success": True, "categories": categories}


@app.post("/api/admin/category-order")
async def admin_update_category_order(body: UpdateCategoryOrderRequest, _=Depends(get_required_admin)):
    CATEGORY_ORDER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CATEGORY_ORDER_FILE, "w", encoding="utf-8") as f:
        json.dump({"order": body.order}, f, indent=4)
    return {"success": True}


@app.post("/api/admin/ui-labels")
async def admin_update_ui_labels(body: UpdateUILabelsRequest, _=Depends(get_required_admin)):
    UI_LABELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(UI_LABELS_FILE, "w", encoding="utf-8") as f:
        json.dump(body.labels, f, indent=4)
    return {"success": True}


@app.post("/api/admin/branding")
async def admin_update_branding(body: UpdateBrandingRequest, _=Depends(get_required_admin)):
    BRANDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    safe_keys = ["brand_name", "app_title", "primary_color", "secondary_color", "bg_core", "bg_panel", "text_color", "icon_reference"]
    branding = {k: v for k, v in body.branding.items() if k in safe_keys}
    with open(BRANDING_FILE, "w", encoding="utf-8") as f:
        json.dump(branding, f, indent=4)
    return {"success": True}


@app.post("/api/admin/password")
async def admin_change_password(body: UpdateAdminPasswordRequest, _=Depends(get_required_admin)):
    expected = get_admin_password()
    if body.current_password != expected:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters")
    ADMIN_PASSWORD_FILE.write_text(body.new_password + "\n", encoding="utf-8")
    return {"success": True}


@app.post("/api/admin/upload-master")
async def upload_master_excel(
    file: UploadFile = File(...),
    _=Depends(get_required_admin),
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are accepted.")

    ITEM_MASTER_DIR.mkdir(parents=True, exist_ok=True)
    master_path = ITEM_MASTER_DIR / "Master.xlsx"

    if master_path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak_path = ITEM_MASTER_DIR / f"Master_{ts}.bak"
        shutil.copy2(master_path, bak_path)
        logger.info(f"Backed up Master.xlsx to {bak_path.name}")

    content = await file.read()
    with open(master_path, "wb") as f:
        f.write(content)
    logger.info(f"Uploaded new Master.xlsx ({len(content):,} bytes)")

    success = convert_excel_to_json()
    if success:
        return {"success": True, "message": f"Master.xlsx uploaded ({len(content):,} bytes) and inventory rebuilt successfully."}
    else:
        return {"success": False, "message": "File uploaded but inventory rebuild failed. Check that the sheet format is correct (Column A = English, Column B = Spanish, tab name = Category (icon))."}


@app.get("/admin")
async def admin_panel():
    return FileResponse("web/admin.html")


app.mount("/", StaticFiles(directory="web", html=True), name="web")


def get_port():
    try:
        with open("port.txt", "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 5000


if __name__ == "__main__":
    port = get_port()
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
