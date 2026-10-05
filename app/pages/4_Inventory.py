import streamlit as st
import pandas as pd
import importlib
import data_manager
import db

# Force reload db module to avoid stale module cache in Streamlit
try:
    importlib.reload(db)
except Exception:
    pass

st.set_page_config(
    page_title="Inventory — Saffron Court",
    page_icon="📦",
    layout="wide"
)

# Custom High-Contrast RMS Styling
st.markdown("""
<style>
    .page-header {
        color: #FFB703 !important;
        font-family: 'Playfair Display', Georgia, serif;
        font-weight: 700;
        margin-bottom: 0.1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1A1E24;
        padding: 6px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        color: #94A3B8 !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFB703 !important;
        color: #0F172A !important;
        font-weight: 700 !important;
    }
    .reorder-card {
        background-color: #2D1A10;
        border: 1px solid #F59E0B;
        border-left: 6px solid #FF9F1C;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .footer-text {
        text-align: center;
        color: #64748B;
        font-size: 0.9rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="page-header">📦 Inventory Management</h1>', unsafe_allow_html=True)
st.caption("Monitor stock levels and reorder lists.")

# Load stock items and recipes safely
stock_items = getattr(db, "get_inventory_stock", lambda: [])()
recipes_df = data_manager.load_recipes()
menu_df = data_manager.load_menu()

# Build recipe mapping: ingredient_id -> list of dish names
ing_dish_map = {}
if not recipes_df.empty and not menu_df.empty:
    merged = pd.merge(recipes_df, menu_df, on="dish_id")
    for ing_id, group in merged.groupby("ingredient_id"):
        ing_dish_map[ing_id] = list(group["name"].unique())

tabs = st.tabs(["📊 Stock Levels & Reorder List", "➕ Restock & Ingredient Entry", "🍳 Dish Recipe Usage"])

# ==========================================
# TAB 1: STOCK LEVELS & REORDER LIST
# ==========================================
with tabs[0]:
    st.subheader("Live Inventory Stock Levels")
    
    # Ingredient ID Filter Dropdown
    ing_filter_opts = ["All Ingredients"] + [f"{item['ingredient_id']} - {item['name']}" for item in stock_items]
    selected_ing_filter = st.selectbox("🔍 Filter by Ingredient ID:", ing_filter_opts)
    
    selected_filter_id = None
    if selected_ing_filter != "All Ingredients":
        selected_filter_id = selected_ing_filter.split(" - ")[0].strip()
    
    # Identify items below reorder level
    reorder_items = [item for item in stock_items if float(item["stock_qty"]) <= float(item["reorder_level"])]
    if selected_filter_id:
        reorder_items = [item for item in reorder_items if item["ingredient_id"] == selected_filter_id]
        
    st.divider()
    
    if reorder_items:
        st.markdown(f"### ⚠️ Reorder List ({len(reorder_items)} items low in stock)")
        reorder_table = []
        for item in reorder_items:
            reorder_table.append({
                "Ingredient ID": item["ingredient_id"],
                "Name": item["name"],
                "Current Stock": f"{item['stock_qty']:.2f} {item['unit']}",
                "Reorder Threshold": f"{item['reorder_level']:.2f} {item['unit']}",
                "Dishes Affected": ", ".join(ing_dish_map.get(item["ingredient_id"], ["None"]))
            })
        st.dataframe(pd.DataFrame(reorder_table), hide_index=True, use_container_width=True)
    else:
        st.success("✅ All ingredient stock levels are above their reorder threshold!")
        
    st.divider()
    st.markdown("### 📋 Complete Ingredient Inventory Table")
    
    if not stock_items:
        st.warning("No inventory stock data found.")
    else:
        display_stock = stock_items
        if selected_filter_id:
            display_stock = [item for item in stock_items if item["ingredient_id"] == selected_filter_id]
            
        full_table = []
        for item in display_stock:
            is_low = float(item["stock_qty"]) <= float(item["reorder_level"])
            full_table.append({
                "Ingredient ID": item["ingredient_id"],
                "Name": item["name"],
                "Unit": item["unit"],
                "Current Stock": f"{item['stock_qty']:.2f}",
                "Reorder Level": f"{item['reorder_level']:.2f}",
                "Status": "⚠️ LOW STOCK" if is_low else "OK",
                "Used In Dishes": ", ".join(ing_dish_map.get(item["ingredient_id"], ["None"]))
            })
        st.dataframe(pd.DataFrame(full_table), hide_index=True, use_container_width=True)


# ==========================================
# TAB 2: RESTOCK & INGREDIENT ENTRY
# ==========================================
with tabs[1]:
    st.subheader("➕ Restock & Add New Ingredients")
    st.caption("Select an Ingredient ID from the dropdown to automatically populate ingredient details and update stock.")
    
    # Load all inventory stock items
    stock_items = getattr(db, "get_inventory_stock", lambda: [])()
    inv_map = {item["ingredient_id"]: item for item in stock_items}
    
    # Pre-populate missing I61 if not present
    if "I61" not in inv_map:
        inv_map["I61"] = {"ingredient_id": "I61", "name": "Truffle Oil", "unit": "l", "stock_qty": 2.0, "reorder_level": 0.5}
        
    known_ids = sorted(list(inv_map.keys()))
    dropdown_opts = [f"{i_id} - {inv_map[i_id]['name']}" for i_id in known_ids]
    dropdown_opts.append("+ Add New Custom Ingredient ID")
    
    selected_ing_choice = st.selectbox("Select Ingredient ID to Update / Restock", dropdown_opts, index=0)
    
    if selected_ing_choice.startswith("+"):
        ing_id_in = "I62"
        info = {}
    else:
        ing_id_in = selected_ing_choice.split(" - ")[0].strip()
        info = inv_map.get(ing_id_in, {})
        
    default_name = info.get("name", "")
    default_unit = info.get("unit", "kg")
    default_stock = float(info.get("stock_qty", 10.0))
    default_reorder = float(info.get("reorder_level", 5.0))
    
    unit_options = ["kg", "l", "pcs", "g", "ml"]
    unit_index = unit_options.index(default_unit) if default_unit in unit_options else 0
    
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        ing_id_display = st.text_input("Ingredient ID", value=ing_id_in)
        ing_name_in = st.text_input("Ingredient Name", value=default_name, placeholder="e.g. Chicken breast")
        ing_unit_in = st.selectbox("Measurement Unit", unit_options, index=unit_index)
    with col_i2:
        ing_stock_in = st.number_input("Stock Quantity", min_value=0.0, value=default_stock, step=1.0)
        ing_reorder_in = st.number_input("Reorder Level Threshold", min_value=0.0, value=default_reorder, step=1.0)
        
    if st.button("💾 Save / Restock Ingredient"):
        if not ing_id_display.strip() or not ing_name_in.strip():
            st.error("Please enter a valid Ingredient ID and Name.")
        else:
            success, msg = db.update_inventory_stock(
                ing_id_display.strip(),
                ing_name_in.strip(),
                ing_unit_in.strip(),
                ing_stock_in,
                ing_reorder_in
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


# ==========================================
# TAB 3: DISH RECIPE USAGE
# ==========================================
with tabs[2]:
    st.subheader("🍳 Dish Recipe Breakdown")
    if recipes_df.empty:
        st.warning("No recipe data loaded.")
    else:
        selected_dish = st.selectbox("Select Dish to View Ingredients", menu_df["name"].unique() if not menu_df.empty else [])
        if selected_dish:
            dish_row = menu_df[menu_df["name"] == selected_dish].iloc[0]
            d_id = dish_row["dish_id"]
            
            d_recipes = recipes_df[recipes_df["dish_id"] == d_id]
            if d_recipes.empty:
                st.info(f"No recipe breakdown listed for '{selected_dish}'.")
            else:
                inv_stock_list = getattr(db, "get_inventory_stock", lambda: [])()
                inv_map = {item["ingredient_id"]: item for item in inv_stock_list}
                
                recipe_table = []
                for _, r in d_recipes.iterrows():
                    i_id = r["ingredient_id"]
                    inv_info = inv_map.get(i_id, {})
                    recipe_table.append({
                        "Ingredient ID": i_id,
                        "Ingredient Name": inv_info.get("name", "Unknown / Missing"),
                        "Quantity per Portion": f"{r['qty_per_portion']} {r['unit']}",
                        "Current Stock Available": f"{inv_info.get('stock_qty', 0.0):.2f} {inv_info.get('unit', '')}" if inv_info else "❌ Missing from Stock"
                    })
                st.dataframe(pd.DataFrame(recipe_table), hide_index=True, use_container_width=True)

# Mandatory Footer
st.markdown('<p class="footer-text">Saffron Court Internal Management App</p>', unsafe_allow_html=True)
