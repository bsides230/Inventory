import json
import logging
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import jwt
import pandas as pd
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from db.auth import AuthenticatedUser, get_optional_authenticated_user, get_required_authenticated_user
from db.database import get_session
from db.repositories import OrderDraftRepository, OrderRepository, UserRepository
from services.email_delivery import OrderEmailDeliveryService, SmtpEmailClient
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


# --- Config helpers ---
def load_locations() -> dict[str, str]:
    """Load PIN->LocationName mapping from locations.txt"""
    result = {}
    if not LOCATIONS_CONFIG.exists():
        return result
    with open(LOCATIONS_CONFIG, "r") as f:
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
    LOCATIONS_CONFIG.write_text("\n".join(lines) + "\n")


def get_admin_password() -> str:
    if ADMIN_PASSWORD_FILE.exists():
        return ADMIN_PASSWORD_FILE.read_text().strip()
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
    with open(EMAIL_SETTINGS_FILE, "r") as f:
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
    EMAIL_SETTINGS_FILE.write_text("\n".join(lines) + "\n")


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
    with open(RECIPIENTS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def save_recipients(recipients: list[str]) -> None:
    lines = ["# Order recipient emails (one per line)"] + recipients
    RECIPIENTS_FILE.write_text("\n".join(lines) + "\n")


@dataclass
class NullOrderEmailDeliveryService:
    error: str

    def send_order_email(self, **kwargs):
        from services.email_delivery import EmailDeliveryResult
        return EmailDeliveryResult(status="failed", attempts=0, error=self.error)


def get_location_name():
    if LOCATION_FILE.exists():
        with open(LOCATION_FILE, "r") as f:
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
WEB_DIR.mkdir(exist_ok=True)
FLAGS_DIR.mkdir(exist_ok=True)
ITEM_MASTER_DIR.mkdir(exist_ok=True)
ORDERS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

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
        with open(CATEGORIES_FILE, "r") as f:
            return json.load(f)
    return {}


def save_categories_config(config: Dict[str, dict]):
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(config, f, indent=4)


def get_inventory_category(category: str):
    check_and_update()
    cat_file = DATA_DIR / f"{category}.json"
    if cat_file.exists():
        try:
            with open(cat_file, "r") as f:
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


class SubmitOrderRequest(BaseModel):
    date: str
    is_rush: bool
    needed_by: Optional[str] = None
    draft_id: Optional[int] = None


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

    with get_session(settings.database_url) as session:
        users = UserRepository(session)
        external_id = f"pin_{pin}"
        user = users.get_by_external_id(external_id)
        if user is None:
            user = users.create(
                external_id=external_id,
                email=f"{external_id}@location.local",
                display_name=location_name,
            )
        else:
            user.display_name = location_name

    payload = {
        "sub": f"pin_{pin}",
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
    return {"status": "ready", "checks": {"data_dir": DATA_DIR.exists(), "categories_file": CATEGORIES_FILE.exists()}}


@app.get("/api/version")
async def get_version():
    return {"version": settings.app_version, "environment": settings.app_env}


@app.get("/api/status")
async def get_status():
    return {"status": "online", "location": get_location_name()}


@app.get("/api/categories")
async def get_categories():
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
                "icon": cat_config.get("icon", "box"),
                "color": cat_config.get("color", "gray"),
            })
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
        if user:
            with get_session(settings.database_url) as session:
                drafts = OrderDraftRepository(session)
                if draft_id:
                    draft = drafts.get_by_id_for_user(draft_id, user.id, with_items=True)
                else:
                    draft = drafts.get_active_for_user(user.id, with_items=True)
                if draft:
                    draft_quantities = {item.item_id: (item.quantity, item.unit) for item in draft.items}

        response_items = []
        for item in items:
            quantity, unit = draft_quantities.get(item["id"], (0, "each"))
            response_items.append({**item, "qty": quantity, "unit": unit})

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

    with get_session(settings.database_url) as session:
        drafts = OrderDraftRepository(session)
        if draft_id:
            draft = drafts.get_by_id_for_user(draft_id, user.id)
            if draft is None:
                raise HTTPException(status_code=404, detail="Draft not found")
        else:
            draft = drafts.get_or_create_active_for_user(user.id)

        if request.qty <= 0:
            drafts.remove_item(draft.id, request.id)
        else:
            drafts.add_or_update_item(
                draft_id=draft.id,
                item_id=request.id,
                category_id=category_lower,
                item_name=target_item.get("name_en", target_item.get("name", request.id)),
                quantity=request.qty,
                unit=request.unit,
            )

    return {"success": True}


# --- Draft Management Endpoints ---
@app.get("/api/drafts")
async def list_drafts(user: AuthenticatedUser = Depends(get_required_authenticated_user)):
    with get_session(settings.database_url) as session:
        drafts_repo = OrderDraftRepository(session)
        all_drafts = drafts_repo.get_all_active_for_user(user.id)
        result = []
        for d in all_drafts:
            item_count = drafts_repo.count_items(d.id)
            result.append({
                "id": d.id,
                "name": d.draft_name or f"Draft {d.id}",
                "item_count": item_count,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })
    return {"success": True, "drafts": result}


@app.post("/api/drafts/new")
async def create_draft(body: NewDraftRequest, user: AuthenticatedUser = Depends(get_required_authenticated_user)):
    with get_session(settings.database_url) as session:
        drafts_repo = OrderDraftRepository(session)
        existing = drafts_repo.get_all_active_for_user(user.id)
        name = body.name or f"Draft {len(existing) + 1}"
        draft = drafts_repo.create(user_id=user.id, draft_name=name)
        draft_id = draft.id
        draft_name = draft.draft_name
    return {"success": True, "draft": {"id": draft_id, "name": draft_name, "item_count": 0}}


@app.post("/api/drafts/{draft_id}/rename")
async def rename_draft(
    draft_id: int,
    body: RenameDraftRequest,
    user: AuthenticatedUser = Depends(get_required_authenticated_user),
):
    with get_session(settings.database_url) as session:
        drafts_repo = OrderDraftRepository(session)
        draft = drafts_repo.get_by_id_for_user(draft_id, user.id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Draft not found")
        drafts_repo.rename(draft_id, body.name)
    return {"success": True}


@app.delete("/api/drafts/{draft_id}")
async def delete_draft(draft_id: int, user: AuthenticatedUser = Depends(get_required_authenticated_user)):
    with get_session(settings.database_url) as session:
        drafts_repo = OrderDraftRepository(session)
        deleted = drafts_repo.delete(draft_id, user.id)
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

    if request.is_rush and request.needed_by:
        filename = f"{location} URGENT ORDER by {request.needed_by}.xlsx"
    else:
        date_str = request.date.replace("/", "-")
        filename = f"{location} Falcones Order {date_str}.xlsx"

    filepath = ORDERS_DIR / filename

    try:
        with get_session(settings.database_url) as session:
            drafts = OrderDraftRepository(session)
            orders = OrderRepository(session)

            if request.draft_id:
                draft = drafts.get_by_id_for_user(request.draft_id, user.id, with_items=True)
            else:
                draft = drafts.get_active_for_user(user.id, with_items=True)

            if draft is None or not draft.items:
                return {"success": False, "message": "No items to order."}

            draft.is_rush = request.is_rush
            draft.needed_by = request.needed_by

            order_items = []
            for draft_item in draft.items:
                category_data = get_inventory_category(draft_item.category_id)
                category_label = category_data["label"] if category_data else draft_item.category_id
                order_items.append({
                    "Category": category_label,
                    "Item Name": draft_item.item_name,
                    "Quantity": draft_item.quantity,
                    "Unit": draft_item.unit,
                })

            df = pd.DataFrame(order_items).sort_values(by="Category")
            df.to_excel(filepath, index=False)
            order = orders.create_from_draft(
                draft,
                export_filename=filename,
                location_pin=location_pin,
                location_name=location_name,
            )

        email_service = build_email_service()
        delivery = email_service.send_order_email(
            order_id=order.id,
            location=location_name or location,
            date=request.date,
            is_rush=request.is_rush,
            needed_by=request.needed_by,
            export_path=filepath,
        )
        with get_session(settings.database_url) as session:
            orders2 = OrderRepository(session)
            orders2.update_delivery_status(
                order_id=order.id,
                status=delivery.status,
                attempts=delivery.attempts,
                error=delivery.error,
            )

        logger.info(
            "Order submitted location_pin=%s location_name=%s file=%s delivery=%s",
            location_pin, location_name, filepath, delivery.status,
        )
        return {
            "success": True,
            "message": "Order submitted successfully",
            "filename": filename,
            "delivery_status": delivery.status,
            "delivery_attempts": delivery.attempts,
            "delivery_error": delivery.error,
        }
    except Exception as exc:
        if filepath.exists():
            filepath.unlink()
        logger.error("Error saving order: %s", exc, exc_info=True)
        return {"success": False, "message": f"Error saving order: {str(exc)}"}


# --- Admin Endpoints ---
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


@app.post("/api/admin/password")
async def admin_change_password(body: UpdateAdminPasswordRequest, _=Depends(get_required_admin)):
    expected = get_admin_password()
    if body.current_password != expected:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters")
    ADMIN_PASSWORD_FILE.write_text(body.new_password + "\n")
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
        with open("port.txt", "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 5000


if __name__ == "__main__":
    port = get_port()
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
