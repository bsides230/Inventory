import json
import pandas as pd
from pathlib import Path

# Load existing JSON
with open('inventory_data.json', 'r') as f:
    data = json.load(f)

# A manual dictionary of translations for the items
# This is a basic translation for common pizza inventory items.
# I'll use a translation script or write a dictionary.
