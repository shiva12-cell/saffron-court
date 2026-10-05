import os
import pandas as pd
import docx

# Path configuration relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data"))

SUBCATEGORY_MAP = {
    "S01": "Mezzes & Dips",
    "S02": "Soups",
    "S03": "Salads",
    "S04": "Hot Starters",
    "S05": "Hot Starters",
    "S06": "Salads",
    "S07": "Hot Starters",
    "S08": "Salads",
    "S09": "Mezzes & Dips",
    
    "M01": "Rice & Grains",
    "M02": "Seafood Mains",
    "M03": "Rice & Grains",
    "M04": "Rice & Grains",
    "M05": "Curries & Stews",
    "M06": "Curries & Stews",
    "M07": "Pasta",
    "M08": "Chef's Special",
    "M09": "Meat Mains",
    
    "G01": "Grills & Kebabs",
    "G02": "Grills & Kebabs",
    "G03": "Grills & Kebabs",
    "G04": "Grills & Kebabs",
    "G05": "Seafood Grills",
    "G06": "Burgers & Sandwiches",
    
    "D01": "Traditional Desserts",
    "D02": "Traditional Desserts",
    "D03": "Puddings & Cakes",
    "D04": "Puddings & Cakes",
    "D05": "Fresh Fruit",
    "D06": "Puddings & Cakes",
    "D07": "Traditional Desserts",
    
    "B01": "Fresh Juices",
    "B02": "Tea & Coffee",
    "B03": "Tea & Coffee",
    "B04": "Water",
    "B05": "Fresh Juices",
    "B06": "Mocktails",
    "B07": "Tea & Coffee",
    "B08": "Specialty Drinks",
    "B09": "Fresh Juices"
}

def load_menu():
    """Load menu dataset and enrich with subcategories."""
    try:
        path = os.path.join(DATA_DIR, "menu.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path)
        # Convert price_aed to numeric, coerce errors to NaN
        df["price_aed"] = pd.to_numeric(df["price_aed"], errors="coerce")
        df["subcategory"] = df["dish_id"].map(lambda x: SUBCATEGORY_MAP.get(x, "General"))
        # Ensure allergens is string
        df["allergens"] = df["allergens"].fillna("")
        df["kids_friendly"] = df["kids_friendly"].astype(str).str.strip().str.lower()
        df["active"] = df["active"].astype(str).str.strip().str.lower()
        return df
    except Exception:
        return pd.DataFrame()

def load_tables():
    """Load dining tables layout data."""
    try:
        path = os.path.join(DATA_DIR, "tables.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path)
        return df
    except Exception:
        return pd.DataFrame()

def load_reservations():
    """Load baseline reservations from reservations-tonight.csv."""
    try:
        path = os.path.join(DATA_DIR, "reservations-tonight.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path)
        df["notes"] = df["notes"].fillna("")
        df["status"] = df["status"].astype(str).str.strip().str.lower()
        return df
    except Exception:
        return pd.DataFrame()

def load_yesterday_orders():
    """Load historical order line items from yesterday."""
    try:
        path = os.path.join(DATA_DIR, "orders-yesterday.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path)
        df["note"] = df["note"].fillna("")
        return df
    except Exception:
        return pd.DataFrame()

def load_recipes():
    """Load dish recipes data."""
    try:
        path = os.path.join(DATA_DIR, "recipes.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def load_inventory():
    """Load inventory stock levels data."""
    try:
        path = os.path.join(DATA_DIR, "inventory.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def load_staff():
    """Load staff roster data."""
    try:
        path = os.path.join(DATA_DIR, "staff.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def load_house_rules_text():
    """Load house rules text from docx."""
    try:
        path = os.path.join(DATA_DIR, "house-rules.docx")
        if not os.path.exists(path):
            return "House rules document not found."
        doc = docx.Document(path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception:
        return "Unable to load house rules document."
