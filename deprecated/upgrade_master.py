import pandas as pd
from openpyxl import Workbook
import re

xls = pd.ExcelFile('item master/Master.xlsx')
wb = Workbook()
wb.remove(wb.active)

for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)

    # Extract category name from sheet name
    s = sheet_name.strip()
    m = re.match(r'^(.+?)\s*\((.+?)\)\s*$', s)
    if m:
        cat_label_en = m.group(1).strip()
    else:
        m = re.match(r'^(.+?)\s*"(.+?)"\s*$', s)
        if m:
            cat_label_en = m.group(1).strip()
        else:
            cat_label_en = s

    # Spanish category label logic - let's just use the English one for now or check if we can get it from somewhere?
    # Actually, we might have translated category labels in categories.json. Let's load it.
    pass

import json
try:
    with open('categories.json') as f:
        cats = json.load(f)
except:
    cats = {}

# Map cat_label_en to id
for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)

    s = sheet_name.strip()
    m = re.match(r'^(.+?)\s*\((.+?)\)\s*$', s)
    if m:
        cat_label_en = m.group(1).strip()
    else:
        m = re.match(r'^(.+?)\s*"(.+?)"\s*$', s)
        if m:
            cat_label_en = m.group(1).strip()
        else:
            cat_label_en = s

    cat_id = cat_label_en.lower().replace(" ", "_").replace("-", "_")
    cat_config = cats.get(cat_id, {})
    cat_label_en_conf = cat_config.get("label_en", cat_label_en)
    cat_label_es_conf = cat_config.get("label_es", cat_label_en)

    ws = wb.create_sheet(title=sheet_name)

    # Row 1: Language descriptors
    ws.append(['l1: English', 'l2: Español'])
    # Row 2: Category metadata
    ws.append([f'@category: {cat_label_en_conf}', f'@category: {cat_label_es_conf}'])

    # Rows 3+: Items
    for _, row in df.iterrows():
        val1 = str(row[0]) if pd.notna(row[0]) else ''
        val2 = str(row[1]) if len(row) > 1 and pd.notna(row[1]) else ''
        ws.append([val1, val2])

wb.save('item master/Master_new.xlsx')
