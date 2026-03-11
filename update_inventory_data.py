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
DATA_DIR = Path("data")
FLAG_FILE = Path("global_flags/update_inventory.txt")

def load_categories_config() -> dict:
    if CATEGORIES_FILE.exists():
        with open(CATEGORIES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_categories_config(config: dict):
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(config, f, indent=4)

def convert_excel_to_json():
    logging.info("Starting conversion of Excel to JSON...")

    english_file = ITEM_MASTER_DIR / "English Master.xlsx"
    spanish_file = ITEM_MASTER_DIR / "Spanish Master.xlsx"

    if not english_file.exists():
        logging.error("No 'English Master.xlsx' file found in 'item master/' directory.")
        return False

    if not spanish_file.exists():
        logging.error("No 'Spanish Master.xlsx' file found in 'item master/' directory. Proceeding with English only.")

    logging.info(f"Reading Excel files...")

    try:
        xls_en = pd.ExcelFile(english_file)
        xls_es = pd.ExcelFile(spanish_file) if spanish_file.exists() else None

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        config = load_categories_config()
        config_updated = False

        fallback_icons = ["box", "package", "shopping-cart", "archive", "layers"]
        fallback_colors = ["gray", "zinc", "neutral", "stone"]
        icon_idx = 0

        for sheet_name in xls_en.sheet_names:
            df_en = pd.read_excel(xls_en, sheet_name=sheet_name, header=None)
            if df_en.empty or len(df_en.columns) == 0:
                continue

            df_es = None
            if xls_es and sheet_name in xls_es.sheet_names:
                df_es = pd.read_excel(xls_es, sheet_name=sheet_name, header=None)

            # First column contains items
            items_en = df_en[0].dropna().astype(str).tolist()
            if items_en:
                cat_id = sheet_name.lower().replace(" ", "_").replace("-", "_")

                if cat_id not in config:
                    config[cat_id] = {
                        "color": fallback_colors[icon_idx % len(fallback_colors)],
                        "icon": fallback_icons[icon_idx % len(fallback_icons)],
                        "label_en": sheet_name,
                        "label_es": sheet_name
                    }
                    config_updated = True
                    icon_idx += 1
                else:
                    needs_update = False
                    if "label_en" not in config[cat_id]:
                        config[cat_id]["label_en"] = config[cat_id].get("label", sheet_name)
                        needs_update = True
                    if "label_es" not in config[cat_id]:
                        config[cat_id]["label_es"] = config[cat_id].get("label", sheet_name)
                        needs_update = True
                    if "label" in config[cat_id] and "label_en" in config[cat_id] and "label_es" in config[cat_id]:
                        del config[cat_id]["label"]
                        needs_update = True
                    if needs_update:
                        config_updated = True

                category_data = {
                    "label": sheet_name,
                    "items": []
                }

                for i, item_en in enumerate(items_en):
                    item_es = item_en
                    if df_es is not None and i < len(df_es) and len(df_es.columns) > 0:
                        val = df_es.iloc[i, 0]
                        if pd.notna(val):
                            item_es = str(val)

                    category_data["items"].append({
                        "id": f"{cat_id}_{i}",
                        "name_en": item_en,
                        "name_es": item_es
                    })

                # Save individual category JSON file
                json_filepath = DATA_DIR / f"{cat_id}.json"

                # Check if changed to avoid unnecessary writes, though writing is fast
                current_data = None
                if json_filepath.exists():
                    try:
                        with open(json_filepath, "r") as f:
                            current_data = json.load(f)
                    except json.JSONDecodeError:
                        pass

                if current_data != category_data:
                    logging.info(f"Saving new converted data to {json_filepath.name}")
                    with open(json_filepath, "w") as f:
                        json.dump(category_data, f, indent=4)

        if config_updated:
            logging.info("Updating categories.json with new categories.")
            save_categories_config(config)

        # Cleanup obsolete json file if it exists
        if Path("inventory_data.json").exists():
             # We no longer use this file, but we keep it for backup or ignore it.
             pass

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
    elif not DATA_DIR.exists() or not list(DATA_DIR.glob("*.json")):
        # First run logic
        logging.info("No existing JSON data found. Running initial conversion.")
        convert_excel_to_json()

if __name__ == "__main__":
    check_and_update()
