import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from db.auth import AuthenticatedUser, get_optional_authenticated_user, get_required_authenticated_user
from db.database import get_session
from db.repositories import OrderDraftRepository, OrderRepository
from update_inventory_data import check_and_update


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    app_version: str = "0.1.0"
    database_url: str = "sqlite:///./inventory.db"
    auth_jwt_secret: str = "change-me"
    auth_jwt_algorithm: str = "HS256"

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


# --- Initialization ---
LOCATION_FILE = Path("location.txt")
CATEGORIES_FILE = Path("categories.json")
DATA_DIR = Path("data")
ITEM_MASTER_DIR = Path("item master")
ORDERS_DIR = Path("orders")


def get_location_name():
    if LOCATION_FILE.exists():
        with open(LOCATION_FILE, "r") as f:
            return f.read().strip()
    return "Falcones Pizza"


app = FastAPI(title=f"{get_location_name()} Inventory")
app.state.settings = settings

# Setup directories
WEB_DIR = Path("web")
FLAGS_DIR = Path("global_flags")
WEB_DIR.mkdir(exist_ok=True)
FLAGS_DIR.mkdir(exist_ok=True)
ITEM_MASTER_DIR.mkdir(exist_ok=True)
ORDERS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Run initial inventory data conversion check
check_and_update()


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    logger.info(
        "Request started %s %s",
        request.method,
        request.url.path,
        extra={"request_id": request_id},
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "Request completed %s %s status=%s",
        request.method,
        request.url.path,
        response.status_code,
        extra={"request_id": request_id},
    )
    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
class UpdateItemRequest(BaseModel):
    id: str
    qty: int
    unit: str


class SubmitOrderRequest(BaseModel):
    date: str
    is_rush: bool
    needed_by: Optional[str] = None


# --- API Endpoints ---
@app.get("/health/live")
async def health_live():
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready():
    return {
        "status": "ready",
        "checks": {
            "data_dir": DATA_DIR.exists(),
            "categories_file": CATEGORIES_FILE.exists(),
        },
    }


@app.get("/api/version")
async def get_version():
    return {
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@app.get("/api/status")
async def get_status():
    return {"status": "online", "location": get_location_name()}


@app.get("/api/categories")
async def get_categories():
    logger.info("Handling /api/categories request")
    cat_ids = get_all_inventory_categories()
    config = load_categories_config()
    categories = []

    for cat_id in cat_ids:
        cat_data = get_inventory_category(cat_id)
        if cat_data:
            cat_config = config.get(cat_id, {})
            categories.append(
                {
                    "id": cat_id,
                    "label_en": cat_config.get("label_en", cat_config.get("label", cat_data["label"])),
                    "label_es": cat_config.get("label_es", cat_config.get("label", cat_data["label"])),
                    "icon": cat_config.get("icon", "box"),
                    "color": cat_config.get("color", "gray"),
                }
            )
    return {"success": True, "categories": categories}


@app.get("/api/inventory/{category}")
async def get_inventory(category: str, user: AuthenticatedUser | None = Depends(get_optional_authenticated_user)):
    logger.info("Handling /api/inventory/%s request", category)
    category_lower = category.lower()
    cat_data = get_inventory_category(category_lower)

    if cat_data:
        items = cat_data["items"]
        draft_quantities: dict[str, tuple[int, str]] = {}
        if user:
            with get_session(settings.database_url) as session:
                drafts = OrderDraftRepository(session)
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
    user: AuthenticatedUser = Depends(get_required_authenticated_user),
):
    logger.info("Handling /api/inventory/%s/update request for item %s", category, request.id)
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


@app.post("/api/submit_order")
async def submit_order(
    request: SubmitOrderRequest,
    user: AuthenticatedUser = Depends(get_required_authenticated_user),
):
    logger.info("Handling /api/submit_order request")

    location = get_location_name().replace("/", "_").replace("\\", "_")

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

            draft = drafts.get_active_for_user(user.id, with_items=True)
            if draft is None or not draft.items:
                return {"success": False, "message": "No items to order."}

            draft.is_rush = request.is_rush
            draft.needed_by = request.needed_by

            order_items = []
            for draft_item in draft.items:
                category_data = get_inventory_category(draft_item.category_id)
                category_label = category_data["label"] if category_data else draft_item.category_id
                order_items.append(
                    {
                        "Category": category_label,
                        "Item Name": draft_item.item_name,
                        "Quantity": draft_item.quantity,
                        "Unit": draft_item.unit,
                    }
                )

            df = pd.DataFrame(order_items).sort_values(by="Category")
            df.to_excel(filepath, index=False)
            orders.create_from_draft(draft, export_filename=filename)

        logger.info("Order successfully saved to %s", filepath)
        return {"success": True, "message": "Order submitted successfully", "filename": filename}
    except Exception as exc:
        if filepath.exists():
            filepath.unlink()
        logger.error("Error saving order: %s", exc, exc_info=True)
        return {"success": False, "message": f"Error saving order: {str(exc)}"}


app.mount("/", StaticFiles(directory="web", html=True), name="web")


def get_port():
    try:
        with open("port.txt", "r") as f:
            port = int(f.read().strip())
            return port
    except (FileNotFoundError, ValueError):
        return 8030


if __name__ == "__main__":
    port = get_port()
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
