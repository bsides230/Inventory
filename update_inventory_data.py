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
LANGUAGES_FILE = Path("config/languages.json")

def save_languages(langs: list):
    LANGUAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LANGUAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(langs, f, indent=4, ensure_ascii=False)


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

        global_languages = []

        for sheet_name in sheet_names:
            if use_master:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                if df.empty or len(df.columns) == 0:
                    continue

                # Check for language headers in row 0
                has_lang_headers = False
                lang_cols = {} # { lang_code: col_idx }

                if len(df) >= 2:
                    row0_raw = df.iloc[0].astype(str).str.strip().tolist()

                    for i, val in enumerate(row0_raw):
                        if not val or val.lower() == 'nan':
                            continue
                        # Remove 'L1: ', 'L2: ', etc if present
                        name = re.sub(r'^l\d+:\s*', '', val, flags=re.IGNORECASE).strip()
                        code = re.sub(r'[^a-z0-9]', '_', name.lower())
                        lang_cols[code] = {"col_idx": i, "name": name}
                        has_lang_headers = True

                if not has_lang_headers:
                    # Fallback to col 0 = english, col 1 = spanish if possible
                    lang_cols['english'] = {"col_idx": 0, "name": "English"}
                    if len(df.columns) > 1:
                        lang_cols['espa_ol'] = {"col_idx": 1, "name": "Español"}

                # Update global languages based on the first processed sheet
                if not global_languages:
                    for code, info in lang_cols.items():
                        global_languages.append({"code": code, "name": info["name"]})

                start_row = 2 if has_lang_headers else 0
                cat_labels = {}

                if has_lang_headers and len(df) >= 2:
                    for lang_code, info in lang_cols.items():
                        col_idx = info["col_idx"]
                        if col_idx < len(df.columns):
                            val = df.iloc[1, col_idx]
                            if pd.notna(val) and str(val).strip() and str(val).lower() != 'nan':
                                label = str(val).strip()
                                if label.lower().startswith('@category:'):
                                    label = label[10:].strip()
                                cat_labels[lang_code] = label

                items_by_lang = {}
                for lang_code, info in lang_cols.items():
                    col_idx = info["col_idx"]
                    if col_idx < len(df.columns):
                        items_by_lang[lang_code] = df.iloc[start_row:, col_idx].astype(str).tolist()
                    else:
                        items_by_lang[lang_code] = []

                primary_lang_code = list(lang_cols.keys())[0] if lang_cols else "english"
                items_primary = items_by_lang.get(primary_lang_code, [])

                # Clean up items_primary (remove 'nan' and empty strings)
                items_primary_clean = []
                for val in items_primary:
                    if pd.notna(val) and str(val).lower() != 'nan' and str(val).strip():
                        items_primary_clean.append(str(val).strip())
                    else:
                        items_primary_clean.append('') # Keep alignment

                items_primary = items_primary_clean
                items_by_lang[primary_lang_code] = items_primary_clean

            else:
                # Legacy handling for separated English/Spanish Master files
                df_en = pd.read_excel(xls_en, sheet_name=sheet_name, header=None)
                if df_en.empty or len(df_en.columns) == 0:
                    continue
                items_en = df_en.iloc[:, 0].dropna().astype(str).tolist()
                items_en = [v for v in items_en if v and v.lower() != 'nan']
                items_by_lang = {'english': items_en}
                lang_cols = {'english': {"col_idx": 0, "name": "English"}}

                if xls_es and sheet_name in xls_es.sheet_names:
                    df_es = pd.read_excel(xls_es, sheet_name=sheet_name, header=None)
                    items_by_lang['espa_ol'] = df_es.iloc[:, 0].tolist()
                    lang_cols['espa_ol'] = {"col_idx": 1, "name": "Español"}

                if not global_languages:
                    for code, info in lang_cols.items():
                        global_languages.append({"code": code, "name": info["name"]})

                cat_labels = {}
                primary_lang_code = 'english'
                items_primary = items_en

            if not any(items_primary):
                continue

            cat_label_tab, tab_icon = parse_tab_name(sheet_name)
            cat_id = cat_label_tab.lower().replace(" ", "_").replace("-", "_")

            final_label_primary = cat_labels.get(primary_lang_code) if cat_labels.get(primary_lang_code) else cat_label_tab

            if cat_id not in config:
                icon_val = tab_icon if tab_icon else fallback_icons[icon_idx % len(fallback_icons)]
                config[cat_id] = {
                    "color": fallback_colors[icon_idx % len(fallback_colors)],
                    "icon": icon_val,
                }
                for lang in lang_cols:
                    config[cat_id][f"label_{lang}"] = cat_labels.get(lang) if cat_labels.get(lang) else cat_label_tab
                config_updated = True
                icon_idx += 1
            else:
                if tab_icon and config[cat_id].get("icon") != tab_icon:
                    config[cat_id]["icon"] = tab_icon
                    config_updated = True

                for lang in lang_cols:
                    final_label_lang = cat_labels.get(lang) if cat_labels.get(lang) else cat_label_tab
                    if config[cat_id].get(f"label_{lang}") != final_label_lang:
                        config[cat_id][f"label_{lang}"] = final_label_lang
                        config_updated = True

                if "label" in config[cat_id]:
                    del config[cat_id]["label"]
                    config_updated = True
                if "label_en" in config[cat_id]:
                    del config[cat_id]["label_en"]
                    config_updated = True
                if "label_es" in config[cat_id]:
                    del config[cat_id]["label_es"]
                    config_updated = True

            category_data = {"label": final_label_primary, "items": []}

            valid_idx = 0
            for i, item_primary in enumerate(items_primary):
                if not item_primary:
                    continue

                item_data = {
                    "id": f"{cat_id}_{valid_idx}",
                }

                for lang in lang_cols:
                    items_lang_col = items_by_lang.get(lang, [])
                    item_lang = item_primary
                    if i < len(items_lang_col):
                        val = items_lang_col[i]
                        if pd.notna(val) and str(val).lower() != 'nan' and str(val).strip():
                            item_lang = str(val).strip()
                    item_data[f"name_{lang}"] = item_lang.strip()

                category_data["items"].append(item_data)
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

        if global_languages:
            save_languages(global_languages)

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
