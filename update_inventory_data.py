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
                lang_cols = {} # { lang_code: col_idx }

                if len(df) >= 2:
                    row0 = df.iloc[0].astype(str).str.strip().str.lower().tolist()

                    # Instead of hardcoding EN and ES indicators, extract the language codes directly
                    # Look for l1: english, l2: español format, or just "en", "es"
                    # The prompt says: "row 1 defines language codes (e.g., 'en', 'es')" in AGENTS.md, but screenshot shows "l1: English"

                    for i, val in enumerate(row0):
                        if not val or val == 'nan':
                            continue

                        lang_code = None
                        if val.startswith('l1:') or val == 'en' or val == 'english':
                            lang_code = 'en'
                        elif val.startswith('l2:') or val == 'es' or val == 'español' or val == 'spanish':
                            lang_code = 'es'
                        elif re.match(r'^l\d+:\s*(.+)$', val):
                            m = re.match(r'^l\d+:\s*(.+)$', val)
                            # E.g. l3: French -> fr
                            lang_name = m.group(1).lower()
                            if lang_name == 'french': lang_code = 'fr'
                            elif lang_name == 'german': lang_code = 'de'
                            elif lang_name == 'italian': lang_code = 'it'
                            else: lang_code = lang_name[:2]
                        elif len(val) == 2:
                            # Just "en", "es", "fr", etc.
                            lang_code = val

                        if lang_code:
                            lang_cols[lang_code] = i
                            has_lang_headers = True

                if not has_lang_headers:
                    # Fallback to col 0 = en, col 1 = es if possible
                    lang_cols['en'] = 0
                    if len(df.columns) > 1:
                        lang_cols['es'] = 1

                en_col_idx = lang_cols.get('en', 0)

                # Categories translation is always in row 1, so items start at row 2
                start_row = 2 if has_lang_headers else 0

                cat_labels = {}

                if has_lang_headers and len(df) >= 2:
                    for lang_code, col_idx in lang_cols.items():
                        if col_idx < len(df.columns):
                            val = df.iloc[1, col_idx]
                            if pd.notna(val) and str(val).strip() and str(val).lower() != 'nan':
                                label = str(val).strip()
                                if label.lower().startswith('@category:'):
                                    label = label[10:].strip()
                                cat_labels[lang_code] = label

                items_by_lang = {}
                for lang_code, col_idx in lang_cols.items():
                    if col_idx < len(df.columns):
                        items_by_lang[lang_code] = df.iloc[start_row:, col_idx].astype(str).tolist()
                    else:
                        items_by_lang[lang_code] = []

                items_en = items_by_lang.get('en', [])

                # Clean up items_en (remove 'nan' and empty strings)
                items_en_clean = []
                for val in items_en:
                    if pd.notna(val) and str(val).lower() != 'nan' and str(val).strip():
                        items_en_clean.append(str(val).strip())
                    else:
                        items_en_clean.append('') # Keep alignment

                items_en = items_en_clean
                items_by_lang['en'] = items_en_clean

            else:
                df_en = pd.read_excel(xls_en, sheet_name=sheet_name, header=None)
                if df_en.empty or len(df_en.columns) == 0:
                    continue
                items_en = df_en.iloc[:, 0].dropna().astype(str).tolist()
                items_en = [v for v in items_en if v and v.lower() != 'nan']
                items_by_lang = {'en': items_en}

                if xls_es and sheet_name in xls_es.sheet_names:
                    df_es = pd.read_excel(xls_es, sheet_name=sheet_name, header=None)
                    items_by_lang['es'] = df_es.iloc[:, 0].tolist()
                cat_labels = {}
                lang_cols = {'en': 0}
                if 'es' in items_by_lang:
                    lang_cols['es'] = 1

            # Only proceed if there is at least one valid English item
            if not any(items_en):
                continue

            cat_label_tab, tab_icon = parse_tab_name(sheet_name)
            cat_id = cat_label_tab.lower().replace(" ", "_").replace("-", "_")

            # Fallback to tab name if not found in Excel row 1
            final_label_en = cat_labels.get('en') if cat_labels.get('en') else cat_label_tab

            if cat_id not in config:
                icon_val = tab_icon if tab_icon else fallback_icons[icon_idx % len(fallback_icons)]
                config[cat_id] = {
                    "color": fallback_colors[icon_idx % len(fallback_colors)],
                    "icon": icon_val,
                }
                config[cat_id]["label_en"] = final_label_en
                for lang in lang_cols:
                    if lang != 'en':
                        config[cat_id][f"label_{lang}"] = cat_labels.get(lang) if cat_labels.get(lang) else cat_label_tab
                config_updated = True
                icon_idx += 1
            else:
                if tab_icon and config[cat_id].get("icon") != tab_icon:
                    config[cat_id]["icon"] = tab_icon
                    config_updated = True

                if config[cat_id].get("label_en") != final_label_en:
                    config[cat_id]["label_en"] = final_label_en
                    config_updated = True

                for lang in lang_cols:
                    if lang != 'en':
                        final_label_lang = cat_labels.get(lang) if cat_labels.get(lang) else cat_label_tab
                        if config[cat_id].get(f"label_{lang}") != final_label_lang:
                            config[cat_id][f"label_{lang}"] = final_label_lang
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

                item_data = {
                    "id": f"{cat_id}_{valid_idx}",
                    "name_en": item_en.strip()
                }

                for lang in lang_cols:
                    if lang != 'en':
                        items_lang_col = items_by_lang.get(lang, [])
                        item_lang = item_en
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
