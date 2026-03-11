import os
import json
from pathlib import Path
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

import logging
from update_inventory_data import check_and_update

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
    # Make sure we're always working with latest data
    check_and_update()

    cat_file = DATA_DIR / f"{category}.json"
    if cat_file.exists():
        try:
            with open(cat_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error reading {category}.json: {e}", exc_info=True)
            return None
    return None

def get_all_inventory_categories():
    check_and_update()
    categories = []
    if DATA_DIR.exists():
        for file in DATA_DIR.glob("*.json"):
            categories.append(file.stem)
    return categories

# --- State Management ---
STATE_FILE = Path("inventory_state.json")

def load_inventory_state() -> Dict[str, dict]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_inventory_state(state: Dict[str, dict]):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

INVENTORY_STATE = load_inventory_state()

# --- Models ---
class UpdateItemRequest(BaseModel):
    id: str
    qty: int
    unit: str

class SubmitOrderRequest(BaseModel):
    date: str
    is_rush: bool
    needed_by: Optional[str] = None

# Configure logging for the backend debug system
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- API Endpoints ---
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
            categories.append({
                "id": cat_id,
                "label": cat_config.get("label", cat_data["label"]),
                "icon": cat_config.get("icon", "box"),
                "color": cat_config.get("color", "gray")
            })
    return {"success": True, "categories": categories}

@app.get("/api/inventory/{category}")
async def get_inventory(category: str):
    logger.info(f"Handling /api/inventory/{category} request")
    category_lower = category.lower()
    cat_data = get_inventory_category(category_lower)

    if cat_data:
        items = cat_data["items"]
        # Populate current state
        for item in items:
            state = INVENTORY_STATE.get(item["id"], {"qty": 0, "unit": "each"})
            item["qty"] = state["qty"]
            item["unit"] = state["unit"]

        return {"success": True, "items": items}

    return {"success": True, "items": []}

@app.post("/api/inventory/{category}/update")
async def update_inventory(category: str, request: UpdateItemRequest):
    logger.info(f"Handling /api/inventory/{category}/update request for item {request.id}")
    INVENTORY_STATE[request.id] = {
        "qty": request.qty,
        "unit": request.unit
    }
    save_inventory_state(INVENTORY_STATE)
    return {"success": True}

@app.post("/api/submit_order")
async def submit_order(request: SubmitOrderRequest):
    logger.info(f"Handling /api/submit_order request")

    order_items = []
    cat_ids = get_all_inventory_categories()

    for cat_id in cat_ids:
        cat_data = get_inventory_category(cat_id)
        if cat_data:
            for item in cat_data["items"]:
                item_id = item["id"]
                state = INVENTORY_STATE.get(item_id)
                if state and state.get("qty", 0) > 0:
                    order_items.append({
                        "Category": cat_data["label"],
                        "Item Name": item.get("name_en", item.get("name", "")),
                        "Quantity": state["qty"],
                        "Unit": state["unit"]
                    })

    if not order_items:
        return {"success": False, "message": "No items to order."}

    # Generate Excel
    df = pd.DataFrame(order_items)

    # Sort by Category
    df = df.sort_values(by="Category")

    location = get_location_name().replace("/", "_").replace("\\", "_")

    if request.is_rush and request.needed_by:
        filename = f"{location} URGENT ORDER by {request.needed_by}.xlsx"
    else:
        date_str = request.date.replace("/", "-")
        filename = f"{location} Falcones Order {date_str}.xlsx"

    filepath = ORDERS_DIR / filename

    try:
        df.to_excel(filepath, index=False)

        # Clear state after successful order
        INVENTORY_STATE.clear()
        save_inventory_state(INVENTORY_STATE)

        logger.info(f"Order successfully saved to {filepath}")
        return {"success": True, "message": "Order submitted successfully", "filename": filename}
    except Exception as e:
        logger.error(f"Error saving order: {e}", exc_info=True)
        return {"success": False, "message": f"Error saving order: {str(e)}"}

# --- Static Files ---
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
