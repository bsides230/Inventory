import json
import re
import shutil
from datetime import datetime
from pathlib import Path
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ITEM_MASTER_DIR = Path("item master")
CATEGORIES_FILE = Path("categories.json")
DATA_DIR = Path("data")
FLAG_FILE = Path("global_flags/update_inventory.txt")
MASTER_FILE = ITEM_MASTER_DIR / "Master.xlsx"


def load_categories_config() -> dict:
    if CATEGORIES_FILE.exists():
        with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_categories_config(config: dict):
    with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def parse_tab_name(tab_name: str):
    """
    Parse category name and icon from a sheet tab name.
    Supported formats:
      "Pizza (🍕)"   -> name="Pizza", icon="🍕"
      'Pizza "🍕"'  -> name="Pizza", icon="🍕"
    Falls back to full tab name with no icon.
    Returns (name, icon_or_None)
    """
    s = tab_name.strip()
    # Parenthesis format: "Name (icon)"
    m = re.match(r'^(.+?)\s*\((.+?)\)\s*$', s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # Double-quotes format: 'Name "icon"'
    m = re.match(r'^(.+?)\s*"(.+?)"\s*$', s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return s, None


def backup_master():
    """Backup existing Master.xlsx to a timestamped .bak file."""
    if MASTER_FILE.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = ITEM_MASTER_DIR / f"Master_{ts}.bak"
        shutil.copy2(MASTER_FILE, bak)
        logging.info(f"Backed up Master.xlsx to {bak.name}")
        return bak
    return None


def convert_excel_to_json():
    logging.info("Starting conversion of Excel to JSON...")

    use_master = MASTER_FILE.exists()
    english_file = ITEM_MASTER_DIR / "English Master.xlsx"
    spanish_file = ITEM_MASTER_DIR / "Spanish Master.xlsx"

    if not use_master and not english_file.exists():
        logging.error("No Master.xlsx or English Master.xlsx found in 'item master/' directory.")
        return False

    logging.info(f"Reading {'Master.xlsx' if use_master else 'English/Spanish Master files'}...")

    try:
        if use_master:
            xls = pd.ExcelFile(MASTER_FILE)
            sheet_names = xls.sheet_names
        else:
            xls_en = pd.ExcelFile(english_file)
            xls_es = pd.ExcelFile(spanish_file) if spanish_file.exists() else None
            sheet_names = xls_en.sheet_names

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        config = load_categories_config()
        config_updated = False

        fallback_icons = ["box", "package", "shopping-cart", "archive", "layers"]
        fallback_colors = ["gray", "zinc", "neutral", "stone"]
        icon_idx = 0

        for sheet_name in sheet_names:
            if use_master:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                if df.empty or len(df.columns) == 0:
                    continue
                items_en = df.iloc[:, 0].astype(str).tolist()
                items_en = [v for v in items_en if v and v.lower() != 'nan']
                items_es_col = df.iloc[:, 1].tolist() if len(df.columns) >= 2 else []
            else:
                df_en = pd.read_excel(xls_en, sheet_name=sheet_name, header=None)
                if df_en.empty or len(df_en.columns) == 0:
                    continue
                items_en = df_en.iloc[:, 0].dropna().astype(str).tolist()
                items_en = [v for v in items_en if v and v.lower() != 'nan']
                items_es_col = []
                if xls_es and sheet_name in xls_es.sheet_names:
                    df_es = pd.read_excel(xls_es, sheet_name=sheet_name, header=None)
                    items_es_col = df_es.iloc[:, 0].tolist()

            if not items_en:
                continue

            cat_label, tab_icon = parse_tab_name(sheet_name)
            cat_id = cat_label.lower().replace(" ", "_").replace("-", "_")

            if cat_id not in config:
                icon_val = tab_icon if tab_icon else fallback_icons[icon_idx % len(fallback_icons)]
                config[cat_id] = {
                    "color": fallback_colors[icon_idx % len(fallback_colors)],
                    "icon": icon_val,
                    "label_en": cat_label,
                    "label_es": cat_label,
                }
                config_updated = True
                icon_idx += 1
            else:
                if tab_icon and config[cat_id].get("icon") != tab_icon:
                    config[cat_id]["icon"] = tab_icon
                    config_updated = True
                if "label_en" not in config[cat_id]:
                    config[cat_id]["label_en"] = cat_label
                    config_updated = True
                if "label_es" not in config[cat_id]:
                    config[cat_id]["label_es"] = cat_label
                    config_updated = True
                if "label" in config[cat_id] and "label_en" in config[cat_id]:
                    del config[cat_id]["label"]
                    config_updated = True

            category_data = {"label": cat_label, "items": []}

            for i, item_en in enumerate(items_en):
                item_es = item_en
                if i < len(items_es_col):
                    val = items_es_col[i]
                    if pd.notna(val) and str(val).lower() != 'nan' and str(val).strip():
                        item_es = str(val).strip()

                category_data["items"].append({
                    "id": f"{cat_id}_{i}",
                    "name_en": item_en.strip(),
                    "name_es": item_es.strip(),
                })

            json_filepath = DATA_DIR / f"{cat_id}.json"
            current_data = None
            if json_filepath.exists():
                try:
                    with open(json_filepath, "r", encoding="utf-8") as f:
                        current_data = json.load(f)
                except json.JSONDecodeError:
                    pass

            if current_data != category_data:
                logging.info(f"Saving {json_filepath.name}")
                with open(json_filepath, "w", encoding="utf-8") as f:
                    json.dump(category_data, f, indent=4, ensure_ascii=False)

        if config_updated:
            logging.info("Updating categories.json")
            save_categories_config(config)

        return True

    except Exception as e:
        logging.error(f"Error converting Excel to JSON: {e}", exc_info=True)
        return False


def check_and_update():
    if not ITEM_MASTER_DIR.exists():
        ITEM_MASTER_DIR.mkdir(parents=True, exist_ok=True)

    if not FLAG_FILE.parent.exists():
        FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)

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
        logging.info("No existing JSON data found. Running initial conversion.")
        convert_excel_to_json()


if __name__ == "__main__":
    check_and_update()
