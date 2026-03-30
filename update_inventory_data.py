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

                # Check for language headers in row 0
                has_lang_headers = False
                en_col_idx = 0
                es_col_idx = 1 if len(df.columns) >= 2 else -1

                if len(df) >= 2:
                    row0 = df.iloc[0].astype(str).str.strip().str.lower().tolist()
                    if 'en' in row0 or 'es' in row0:
                        has_lang_headers = True
                        if 'en' in row0:
                            en_col_idx = row0.index('en')
                        if 'es' in row0:
                            es_col_idx = row0.index('es')

                start_row = 2 if has_lang_headers else 0

                cat_label_en = None
                cat_label_es = None

                if has_lang_headers and len(df) >= 2:
                    val_en = df.iloc[1, en_col_idx] if en_col_idx >= 0 else None
                    if pd.notna(val_en) and str(val_en).strip() and str(val_en).lower() != 'nan':
                        cat_label_en = str(val_en).strip()

                    val_es = df.iloc[1, es_col_idx] if es_col_idx >= 0 else None
                    if pd.notna(val_es) and str(val_es).strip() and str(val_es).lower() != 'nan':
                        cat_label_es = str(val_es).strip()

                items_en = df.iloc[start_row:, en_col_idx].astype(str).tolist() if en_col_idx >= 0 else []
                items_es_col = df.iloc[start_row:, es_col_idx].astype(str).tolist() if es_col_idx >= 0 else []

                # Clean up items_en (remove 'nan' and empty strings)
                items_en_clean = []
                for val in items_en:
                    if pd.notna(val) and str(val).lower() != 'nan' and str(val).strip():
                        items_en_clean.append(str(val).strip())
                    else:
                        items_en_clean.append('') # Keep alignment

                items_en = items_en_clean

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
                cat_label_en = None
                cat_label_es = None

            # Only proceed if there is at least one valid English item
            if not any(items_en):
                continue

            cat_label_tab, tab_icon = parse_tab_name(sheet_name)
            cat_id = cat_label_tab.lower().replace(" ", "_").replace("-", "_")

            # Fallback to tab name if not found in Excel row 1
            final_label_en = cat_label_en if cat_label_en else cat_label_tab
            final_label_es = cat_label_es if cat_label_es else cat_label_tab

            if cat_id not in config:
                icon_val = tab_icon if tab_icon else fallback_icons[icon_idx % len(fallback_icons)]
                config[cat_id] = {
                    "color": fallback_colors[icon_idx % len(fallback_colors)],
                    "icon": icon_val,
                    "label_en": final_label_en,
                    "label_es": final_label_es,
                }
                config_updated = True
                icon_idx += 1
            else:
                if tab_icon and config[cat_id].get("icon") != tab_icon:
                    config[cat_id]["icon"] = tab_icon
                    config_updated = True
                if config[cat_id].get("label_en") != final_label_en:
                    config[cat_id]["label_en"] = final_label_en
                    config_updated = True
                if config[cat_id].get("label_es") != final_label_es:
                    config[cat_id]["label_es"] = final_label_es
                    config_updated = True
                if "label" in config[cat_id]:
                    del config[cat_id]["label"]
                    config_updated = True

            category_data = {"label": final_label_en, "items": []}

            # Filter out empty items that were kept for alignment
            valid_idx = 0
            for i, item_en in enumerate(items_en):
                if not item_en:
                    continue

                item_es = item_en
                if i < len(items_es_col):
                    val = items_es_col[i]
                    if pd.notna(val) and str(val).lower() != 'nan' and str(val).strip():
                        item_es = str(val).strip()

                category_data["items"].append({
                    "id": f"{cat_id}_{valid_idx}",
                    "name_en": item_en.strip(),
                    "name_es": item_es.strip(),
                })
                valid_idx += 1

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

        # --- Cleanup: remove categories/data files not in the new master ---
        if use_master:
            processed_ids = set()
            for sheet_name in sheet_names:
                cat_label, _ = parse_tab_name(sheet_name)
                cat_id = cat_label.lower().replace(" ", "_").replace("-", "_")
                processed_ids.add(cat_id)

            # Remove obsolete data JSON files
            for json_file in DATA_DIR.glob("*.json"):
                cat_id_from_file = json_file.stem
                if cat_id_from_file not in processed_ids:
                    logging.info(f"Removing obsolete category file: {json_file.name}")
                    json_file.unlink()

            # Remove obsolete entries from categories.json
            config_after = load_categories_config()
            stale_keys = [k for k in config_after if k not in processed_ids]
            if stale_keys:
                for k in stale_keys:
                    logging.info(f"Removing obsolete category config: {k}")
                    del config_after[k]
                save_categories_config(config_after)

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
