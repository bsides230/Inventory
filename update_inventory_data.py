import os
import json
import pandas as pd
from pathlib import Path
import logging
import shutil

# Configure logging to show in terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ITEM_MASTER_DIR = Path("item master")
CATEGORIES_FILE = Path("categories.json")
INVENTORY_DATA_FILE = Path("inventory_data.json")
BACKUP_FILE = Path("inventory_data.json.bak")
FLAG_FILE = Path("global_flags/update_inventory.txt")

def load_categories_config() -> dict:
    if CATEGORIES_FILE.exists():
        with open(CATEGORIES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_categories_config(config: dict):
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_master_excel_file():
    for file in ITEM_MASTER_DIR.iterdir():
        if file.suffix == ".xlsx" and not file.name.startswith("~"):
            return file
    return None

def convert_excel_to_json():
    logging.info("Starting conversion of Excel to JSON...")

    excel_file = get_master_excel_file()
    if not excel_file:
        logging.error("No Excel file found in 'item master/' directory.")
        return False

    logging.info(f"Reading Excel file: {excel_file.name}")

    try:
        xls = pd.ExcelFile(excel_file)
        data = {}
        config = load_categories_config()
        config_updated = False

        fallback_icons = ["box", "package", "shopping-cart", "archive", "layers"]
        fallback_colors = ["gray", "zinc", "neutral", "stone"]
        icon_idx = 0

        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            if df.empty or len(df.columns) == 0:
                continue

            # First column contains items
            items = df[0].dropna().astype(str).tolist()
            if items:
                cat_id = sheet_name.lower().replace(" ", "_").replace("-", "_")

                if cat_id not in config:
                    config[cat_id] = {
                        "color": fallback_colors[icon_idx % len(fallback_colors)],
                        "icon": fallback_icons[icon_idx % len(fallback_icons)],
                        "label": sheet_name
                    }
                    config_updated = True
                    icon_idx += 1
                elif "label" not in config[cat_id]:
                    config[cat_id]["label"] = sheet_name
                    config_updated = True

                data[cat_id] = {
                    "label": sheet_name,
                    "items": [{"id": f"{cat_id}_{i}", "name": item} for i, item in enumerate(items)]
                }

        if config_updated:
            logging.info("Updating categories.json with new categories.")
            save_categories_config(config)

        # Check if data changed
        current_data = None
        if INVENTORY_DATA_FILE.exists():
            try:
                with open(INVENTORY_DATA_FILE, "r") as f:
                    current_data = json.load(f)
            except json.JSONDecodeError:
                pass

        if current_data == data:
            logging.info("No changes detected in Excel file compared to existing JSON.")
            return True

        # Backup existing
        if INVENTORY_DATA_FILE.exists():
            logging.info(f"Creating backup of existing data to {BACKUP_FILE.name}")
            shutil.copy2(INVENTORY_DATA_FILE, BACKUP_FILE)

        # Save new data
        logging.info(f"Saving new converted data to {INVENTORY_DATA_FILE.name}")
        with open(INVENTORY_DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

        return True

    except Exception as e:
        logging.error(f"Error converting Excel to JSON: {e}")
        return False

def check_and_update():
    if not ITEM_MASTER_DIR.exists():
        ITEM_MASTER_DIR.mkdir(parents=True, exist_ok=True)

    if not FLAG_FILE.parent.exists():
        FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Check if flag file exists and needs processing
    if FLAG_FILE.exists():
        logging.info("Found update trigger flag.")
        success = convert_excel_to_json()
        if success:
            logging.info("Conversion successful, removing flag file.")
            try:
                FLAG_FILE.unlink()
            except Exception as e:
                logging.error(f"Could not remove flag file: {e}")
        else:
            logging.error("Conversion failed. Flag file kept.")
    elif not INVENTORY_DATA_FILE.exists():
        # First run logic
        logging.info("No existing JSON data found. Running initial conversion.")
        convert_excel_to_json()

if __name__ == "__main__":
    check_and_update()
