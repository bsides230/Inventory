# Master Inventory Format Guide
## For Use with Falcones Pizza Inventory System

This document explains how to create the `Master.xlsx` file that powers the inventory app. It is written for humans and AI assistants that need to generate or update inventory data.

---

## Overview

The inventory system uses a **single Excel file** called `Master.xlsx`. Each sheet tab in the file becomes one category in the ordering app. Each row in a sheet is one inventory item.

---

## File Requirements

| Property | Value |
|---|---|
| File name | `Master.xlsx` |
| File format | Excel 2007+ (.xlsx) |
| Row 1 | **Language Codes** (`en`, `es`) |
| Row 2 | **Category Translations** |
| Row 3+ | **Item Translations** |

---

## Sheet Tab Naming

Each sheet tab must be named with the **category name**. You can optionally embed an icon directly in the tab name using one of these formats:

### Format 1 — Parentheses (recommended)
```
Category Name (🍕)
```
Examples:
- `Produce (🥦)`
- `Meats (🥩)`
- `Dairy (🧀)`
- `Beverages (🥤)`
- `Bakery (🥐)`
- `Frozen & Refrigerated (❄️)`
- `Dry Grocery (🌾)`
- `Cleaning (🧹)`
- `Disposables (🥡)`

### Format 2 — Quotes
```
Category Name "🍕"
```

### Format 3 — No icon
```
Category Name
```
If no icon is provided, the app assigns a default placeholder icon.

---

## Row Layout

To support robust category translations, each sheet must follow this layout:

| Row | Language | Notes |
|---|---|---|
| 1 | `en`, `es` | **Language Codes.** These tell the system which column is English and which is Spanish. |
| 2 | Category Names | **Category Translations.** e.g., "Produce" in the `en` column, "Productos Frescos" in the `es` column. |
| 3+ | Item Names | **Item Translations.** One item per row. Blank cells use the English name as fallback. |

*(Note: If Row 1 does not contain `en` and `es`, the system falls back to a legacy mode where Row 1 is the first item and the tab name is used for both English and Spanish category labels.)*

---

## Example Sheet

**Sheet tab name:** `Produce (🥦)`

| Row | A (English) | B (Spanish) |
|---|---|---|
| 1 | en | es |
| 2 | Produce | Productos Frescos |
| 3 | Broccoli | Brócoli |
| 4 | Tomatoes | Tomates |
| 5 | Romaine Lettuce | Lechuga Romana |
| 6 | Roma Tomatoes | Tomates Roma |
| 7 | Yellow Onions | Cebollas Amarillas |
| 8 | Green Bell Peppers | Pimientos Verdes |
| 9 | Jalapeños | Jalapeños |

---

## Full Example File Structure

```
Master.xlsx
├── Sheet: Produce (🥦)
│     A: English names, B: Spanish names
├── Sheet: Meats (🥩)
│     A: English names, B: Spanish names
├── Sheet: Dairy (🧀)
│     A: English names, B: Spanish names
├── Sheet: Dry Grocery (🌾)
│     A: English names, B: Spanish names
├── Sheet: Frozen & Refrigerated (❄️)
│     A: English names, B: Spanish names
├── Sheet: Beverages (🥤)
│     A: English names, B: Spanish names
├── Sheet: Bakery (🥐)
│     A: English names, B: Spanish names
├── Sheet: Cleaning (🧹)
│     A: English names, B: Spanish names
└── Sheet: Disposables (🥡)
      A: English names, B: Spanish names
```

---

## Important Rules

1. **Every sheet tab must have a unique name.**
2. **Row 1 must contain language codes (`en`, `es`).** Row 2 contains the category translations, and Row 3 starts the items.
3. **English is required.** The Spanish column is optional, and individual Spanish item cells can be blank to fallback to English.
4. **When a new Master.xlsx is uploaded**, all old categories are replaced. Categories not present in the new file are removed from the app. This is intentional — the file is the single source of truth.
5. **Each upload creates a backup** of the previous file (e.g. `Master_20260328_142301.bak`) stored in the `item master/` folder. This can be recovered manually if needed.
6. **Sheet names become category IDs** in the system. Spaces are converted to underscores. The icon is stripped from the ID (e.g. `Produce (🥦)` → category ID `produce`).

---

## Uploading the File

1. Log in to the Admin Panel at `/admin`
2. Go to the **Inventory** tab
3. Drag and drop your `Master.xlsx` onto the upload zone, or click to browse
4. Click **Upload & Rebuild**
5. The app immediately updates with the new inventory

---

## Tips for AI-Generated Inventory Files

- Use `openpyxl` (Python) or any standard Excel library to generate the file.
- Sheet tab names support Unicode emoji — they work natively in modern Excel and in the openpyxl library.
- Keep item names concise but specific. Include pack size if relevant (e.g. `Pepperoni Sliced 25lb`).
- Spanish names should be natural translations, not literal. When in doubt, use the English name as the Spanish fallback.
- Do not include totals, subtotals, or formula cells.
- Items are displayed in the order they appear in the sheet (top to bottom).

### Python Example (openpyxl)

```python
import openpyxl

wb = openpyxl.Workbook()
wb.remove(wb.active)  # remove default sheet

categories = {
    "Produce (🥦)": {
        "label_en": "Produce",
        "label_es": "Productos Frescos",
        "items": [
            ("Broccoli", "Brócoli"),
            ("Tomatoes", "Tomates"),
            ("Romaine Lettuce", "Lechuga Romana"),
        ]
    },
    "Meats (🥩)": {
        "label_en": "Meats",
        "label_es": "Carnes",
        "items": [
            ("Pepperoni Sliced 25lb", "Pepperoni Rebanado 25lb"),
            ("Italian Sausage", "Salchicha Italiana"),
            ("Ground Beef 80/20", "Carne Molida 80/20"),
        ]
    },
}

for tab_name, data in categories.items():
    ws = wb.create_sheet(title=tab_name)
    # Row 1: Language codes
    ws.append(["en", "es"])
    # Row 2: Category translations
    ws.append([data["label_en"], data["label_es"]])
    # Row 3+: Items
    for english, spanish in data["items"]:
        ws.append([english, spanish])

wb.save("Master.xlsx")
print("Master.xlsx created successfully.")
```

### pandas Example

```python
import pandas as pd

categories = {
    "Produce (🥦)": {
        "label_en": "Produce",
        "label_es": "Productos Frescos",
        "items": [("Broccoli", "Brócoli"), ("Tomatoes", "Tomates")]
    },
    "Meats (🥩)": {
        "label_en": "Meats",
        "label_es": "Carnes",
        "items": [("Pepperoni", "Pepperoni"), ("Ground Beef", "Carne Molida")]
    },
}

with pd.ExcelWriter("Master.xlsx", engine="openpyxl") as writer:
    for tab_name, data in categories.items():
        # Build rows: [Row 1, Row 2, Row 3...]
        rows = [
            ["en", "es"],
            [data["label_en"], data["label_es"]]
        ] + data["items"]

        df = pd.DataFrame(rows)
        df.to_excel(writer, sheet_name=tab_name, index=False, header=False)

print("Master.xlsx created.")
```

---

## Suggested Category Icons

| Category | Emoji |
|---|---|
| Produce / Vegetables | 🥦 |
| Meats / Proteins | 🥩 |
| Dairy | 🧀 |
| Seafood | 🐟 |
| Bakery / Bread | 🥐 |
| Dry Grocery / Pantry | 🌾 |
| Frozen & Refrigerated | ❄️ |
| Beverages (RTD) | 🥤 |
| Fountain / BIB | 🧃 |
| Alcohol | 🍺 |
| Cleaning Supplies | 🧹 |
| Disposables / Paper | 🥡 |
| Smallwares / Equipment | 🍴 |
| Prepared / Sauces | 🍲 |
| Desserts / Sweets | 🍰 |
| Spices / Seasonings | 🧂 |
| Oils & Condiments | 🫙 |

---

*Last updated: March 2026*
