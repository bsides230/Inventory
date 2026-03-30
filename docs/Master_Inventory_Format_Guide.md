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
| Header row | **None** — data starts on row 1 |
| Column A | English item name |
| Column B | Spanish item name |

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

## Column Layout

| Column | Language | Notes |
|---|---|---|
| A | English | Required. One item name per row. |
| B | Spanish | Optional. If blank, the English name is used as fallback. |

- **No header row.** Row 1 is the first item.
- **No empty rows between items.** Blank rows stop item reading for that column.
- Item names can include brand names, descriptions, or packaging sizes (e.g. `Mozzarella Shredded 5lb`).

---

## Example Sheet

**Sheet tab name:** `Produce (🥦)`

| A (English) | B (Spanish) |
|---|---|
| Broccoli | Brócoli |
| Tomatoes | Tomates |
| Romaine Lettuce | Lechuga Romana |
| Roma Tomatoes | Tomates Roma |
| Yellow Onions | Cebollas Amarillas |
| Green Bell Peppers | Pimientos Verdes |
| Jalapeños | Jalapeños |

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
2. **Do not include a header row.** Row 1 is always item 1.
3. **Column A is required.** Column B is optional.
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
    "Produce (🥦)": [
        ("Broccoli", "Brócoli"),
        ("Tomatoes", "Tomates"),
        ("Romaine Lettuce", "Lechuga Romana"),
    ],
    "Meats (🥩)": [
        ("Pepperoni Sliced 25lb", "Pepperoni Rebanado 25lb"),
        ("Italian Sausage", "Salchicha Italiana"),
        ("Ground Beef 80/20", "Carne Molida 80/20"),
    ],
    "Dairy (🧀)": [
        ("Mozzarella Shredded 5lb", "Mozzarella Rallada 5lb"),
        ("Ricotta Cheese", "Queso Ricotta"),
        ("Parmesan Grated", "Parmesano Rallado"),
    ],
}

for tab_name, items in categories.items():
    ws = wb.create_sheet(title=tab_name)
    for english, spanish in items:
        ws.append([english, spanish])

wb.save("Master.xlsx")
print("Master.xlsx created successfully.")
```

### pandas Example

```python
import pandas as pd

categories = {
    "Produce (🥦)": [("Broccoli", "Brócoli"), ("Tomatoes", "Tomates")],
    "Meats (🥩)": [("Pepperoni", "Pepperoni"), ("Ground Beef", "Carne Molida")],
}

with pd.ExcelWriter("Master.xlsx", engine="openpyxl") as writer:
    for tab_name, items in categories.items():
        df = pd.DataFrame(items)
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
