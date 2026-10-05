import streamlit as st
import pandas as pd
import importlib
from datetime import datetime
import data_manager
import db

# Force reload db module to avoid stale module cache in Streamlit
try:
    importlib.reload(db)
except Exception:
    pass

st.set_page_config(
    page_title="Menu & Orders — Saffron Court",
    page_icon="📋",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .page-header {
        color: #8B0000;
        font-family: 'Playfair Display', Georgia, serif;
        margin-bottom: 0.1rem;
    }
    .bill-box {
        background-color: #FAFAFA;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 1.2rem;
        margin-top: 1rem;
    }
    .bill-line {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.4rem;
        font-size: 1rem;
    }
    .bill-total {
        font-weight: 700;
        font-size: 1.2rem;
        color: #8B0000;
        border-top: 2px solid #8B0000;
        padding-top: 0.5rem;
    }
    .footer-text {
        text-align: center;
        color: #888888;
        font-size: 0.9rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #E0E0E0;
    }
</style>
""", unsafe_allow_html=True)

# Restaurant Subcategory Sticker Mapping
SUBCATEGORY_STICKERS = {
    "Mezzes & Dips": "🧆",
    "Soups": "🥣",
    "Salads": "🥗",
    "Hot Starters": "🍢",
    "Rice & Grains": "🍚",
    "Seafood Mains": "🐟",
    "Curries & Stews": "🍲",
    "Pasta": "🍝",
    "Chef's Special": "⭐",
    "Meat Mains": "🍖",
    "Grills & Kebabs": "🥩",
    "Seafood Grills": "🐟",
    "Burgers & Sandwiches": "🍔",
    "Traditional Desserts": "🥮",
    "Puddings & Cakes": "🍮",
    "Fresh Fruit": "🍉",
    "Tea & Coffee": "☕",
    "Water": "💧",
    "Fresh Juices": "🥤",
    "Mocktails": "🍹",
    "Specialty Drinks": "🥛"
}

CATEGORY_STICKERS = {
    "Starters": "🥗",
    "Mains": "🍲",
    "Grills": "🥩",
    "Desserts": "🍰",
    "Drinks": "🍹",
    "Chef's Special": "⭐"
}

st.markdown('<h1 class="page-header">📋 Menu & Orders</h1>', unsafe_allow_html=True)
st.caption("Manage menu, orders, and sales history.")

# Load Datasets safely
menu_df = data_manager.load_menu()
tables_df = data_manager.load_tables()
yesterday_df = data_manager.load_yesterday_orders()

# Fetch custom Chef's Special Configuration
cs_config = getattr(db, "get_chefs_special_config", lambda: {
    "dish_id": "M08", "name": "Chef's Special of the Day", "price_aed": 0.0,
    "allergens": "ask", "kids_friendly": "no", "active": "yes", "ingredients": "Chef's daily special preparation"
})()

# Update M08 in menu_df with stored Chef's Special configuration
if not menu_df.empty:
    m08_mask = menu_df["dish_id"] == "M08"
    if m08_mask.any():
        menu_df.loc[m08_mask, "dish_id"] = cs_config["dish_id"]
        menu_df.loc[m08_mask, "name"] = cs_config["name"]
        menu_df.loc[m08_mask, "price_aed"] = cs_config["price_aed"] if cs_config["price_aed"] > 0 else None
        menu_df.loc[m08_mask, "allergens"] = cs_config["allergens"]
        menu_df.loc[m08_mask, "kids_friendly"] = cs_config["kids_friendly"]
        menu_df.loc[m08_mask, "active"] = cs_config["active"]
        menu_df.loc[m08_mask, "category"] = "Chef's Special"
        menu_df.loc[m08_mask, "subcategory"] = "Chef's Special"

# Automatically mark dishes unavailable if ingredient stock cannot cover 1 portion
def safe_get_out_of_stock_dishes():
    try:
        fn = getattr(db, "get_out_of_stock_dishes", None)
        if callable(fn):
            return fn()
        return []
    except Exception:
        return []

out_of_stock_dishes = safe_get_out_of_stock_dishes()
if out_of_stock_dishes and not menu_df.empty:
    menu_df.loc[menu_df["dish_id"].isin(out_of_stock_dishes), "active"] = "no"

# Initialize session state for order cart if not present
if "order_cart" not in st.session_state:
    st.session_state.order_cart = []

tabs = st.tabs(["📖 Menu Directory", "🛒 Create New Order", "📜 Order History"])

# ==========================================
# TAB 1: MENU DIRECTORY
# ==========================================
with tabs[0]:
    st.subheader("Restaurant Menu Directory")
    
    # Manager Section for Chef's Special Configuration & Removal
    with st.expander("⭐ Chef's Special Manager Editor", expanded=False):
        st.caption("Select or enter a Dish ID to automatically populate dish details (Name, Price, Allergens, Kids Friendly, Active Status, Ingredients).")
        
        all_dish_ids = list(menu_df["dish_id"].unique()) if not menu_df.empty else ["M08"]
        if cs_config["dish_id"] not in all_dish_ids:
            all_dish_ids.insert(0, cs_config["dish_id"])
            
        selected_dish_id = st.selectbox("Select Dish ID to Load / Edit", all_dish_ids, index=0)
        
        # Build dish ingredients map from recipes
        recipes_df = data_manager.load_recipes()
        inv_stock_list = getattr(db, "get_inventory_stock", lambda: [])()
        inv_name_map = {item["ingredient_id"]: item["name"] for item in inv_stock_list}

        dish_ingredients_map = {}
        if not recipes_df.empty:
            for d_id, group in recipes_df.groupby("dish_id"):
                parts = []
                for _, r in group.iterrows():
                    ing_n = inv_name_map.get(r["ingredient_id"], r["ingredient_id"])
                    parts.append(f"{ing_n} ({r['qty_per_portion']} {r['unit']})")
                dish_ingredients_map[d_id] = ", ".join(parts)

        # Lookup dish details
        dish_info = {}
        if not menu_df.empty and (menu_df["dish_id"] == selected_dish_id).any():
            d_row = menu_df[menu_df["dish_id"] == selected_dish_id].iloc[0]
            dish_info = {
                "dish_id": str(d_row["dish_id"]),
                "name": str(d_row["name"]),
                "price_aed": float(d_row["price_aed"]) if pd.notna(d_row["price_aed"]) else 0.0,
                "allergens": str(d_row["allergens"]) if pd.notna(d_row["allergens"]) and str(d_row["allergens"]).lower() != "nan" else "None",
                "kids_friendly": str(d_row["kids_friendly"]).lower() if pd.notna(d_row["kids_friendly"]) else "yes",
                "active": str(d_row["active"]).lower() if pd.notna(d_row["active"]) else "yes",
                "ingredients": dish_ingredients_map.get(selected_dish_id, cs_config.get("ingredients", "Chef's special daily ingredients"))
            }
        else:
            dish_info = cs_config

        col_cs1, col_cs2, col_cs3 = st.columns([1.2, 2, 1])
        with col_cs1:
            cs_id_in = st.text_input("Dish ID", value=dish_info["dish_id"])
        with col_cs2:
            cs_name_in = st.text_input("Dish Name", value=dish_info["name"])
        with col_cs3:
            cs_price_in = st.number_input("Price (AED)", min_value=0.0, value=float(dish_info["price_aed"]), step=5.0)
            
        col_cs4, col_cs5, col_cs6 = st.columns([1.5, 1, 1])
        with col_cs4:
            cs_allergen_in = st.text_input("Allergens", value=dish_info["allergens"])
        with col_cs5:
            cs_kids_in = st.selectbox("Kids Friendly", ["no", "yes"], index=1 if dish_info["kids_friendly"] == "yes" else 0)
        with col_cs6:
            cs_active_in = st.selectbox("Active Status", ["yes", "no"], index=1 if dish_info["active"] == "no" else 0)
            
        cs_ing_in = st.text_input("Ingredients / Preparation Details", value=dish_info["ingredients"])
        
        c_btn1, c_btn2 = st.columns([1, 1])
        with c_btn1:
            if st.button("💾 Save Chef's Special Details"):
                new_config = {
                    "dish_id": cs_id_in.strip(),
                    "name": cs_name_in.strip(),
                    "price_aed": cs_price_in,
                    "allergens": cs_allergen_in.strip(),
                    "kids_friendly": cs_kids_in,
                    "active": cs_active_in,
                    "ingredients": cs_ing_in.strip()
                }
                success, msg = db.save_chefs_special_config(new_config)
                if success:
                    st.success(msg)
                    st.rerun()
        with c_btn2:
            if st.button("🗑️ Remove / Deactivate Chef's Special"):
                rem_config = {
                    "dish_id": cs_id_in.strip(),
                    "name": cs_name_in.strip(),
                    "price_aed": 0.0,
                    "allergens": cs_allergen_in.strip(),
                    "kids_friendly": cs_kids_in,
                    "active": "no",
                    "ingredients": cs_ing_in.strip()
                }
                success, msg = db.save_chefs_special_config(rem_config)
                if success:
                    st.success("Chef's Special deactivated and removed from active menu.")
                    st.rerun()

    st.divider()

    if menu_df.empty:
        st.warning("Unable to load menu data. Please verify the menu.csv file in the data folder.")
    else:
        # Category Selector (Includes Chef's Special category explicitly)
        categories = ["All Categories", "Starters", "Mains", "Grills", "Desserts", "Drinks", "Chef's Special"]
        selected_cat = st.selectbox("Filter", categories)
        
        display_df = menu_df.copy()
        if selected_cat != "All Categories":
            display_df = display_df[display_df["category"] == selected_cat]
            
        # Group by Category and display sorted by price
        unique_categories = display_df["category"].unique()
        
        for cat in unique_categories:
            cat_icon = CATEGORY_STICKERS.get(cat, "🍽️")
            st.markdown(f"### {cat_icon} {cat}")
            cat_df = display_df[display_df["category"] == cat].copy()
            
            # Sort by price ascending, placing missing prices at the end
            cat_df["price_sort"] = cat_df["price_aed"].fillna(999999)
            cat_df = cat_df.sort_values(by="price_sort").drop(columns=["price_sort"])
            
            # Group by subcategories
            subcategories = cat_df["subcategory"].unique()
            for subcat in subcategories:
                sub_icon = SUBCATEGORY_STICKERS.get(subcat, "🍽️")
                st.markdown(f"#### {sub_icon} {subcat}")
                subcat_df = cat_df[cat_df["subcategory"] == subcat]
                
                # Format dataframe for display
                table_data = []
                for _, row in subcat_df.iterrows():
                    price_str = f"{row['price_aed']:.2f} AED" if pd.notna(row['price_aed']) and float(row['price_aed']) > 0 else "❌ Missing Price (Unsellable)"
                    allergens_str = row['allergens'] if str(row['allergens']).strip() else "None"
                    
                    status_str = "Available"
                    if row["dish_id"] in out_of_stock_dishes:
                        status_str = "🚫 Out of Stock (Disabled)"
                    elif str(row["active"]).lower() != "yes":
                        status_str = "Unavailable"
                        
                    ing_str = dish_ingredients_map.get(row["dish_id"], cs_config.get("ingredients", "Fresh daily ingredients"))
                    if cat == "Chef's Special" or row["dish_id"] == cs_config["dish_id"]:
                        ing_str = cs_config.get("ingredients", "Chef's daily preparation")

                    dish_entry = {
                        "Dish ID": row["dish_id"],
                        "Dish Name": row["name"],
                        "Price (AED)": price_str,
                        "Allergens": allergens_str,
                        "Kids Friendly": "Yes" if str(row["kids_friendly"]).lower() == "yes" else "No",
                        "Active Status": status_str,
                        "Ingredients": ing_str
                    }
                        
                    table_data.append(dish_entry)
                
                st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)


# ==========================================
# TAB 2: CREATE NEW ORDER
# ==========================================
with tabs[1]:
    st.subheader("🛒 Order Creation & Billing Engine")
    
    col_order_left, col_order_right = st.columns([1.1, 0.9])
    
    with col_order_left:
        st.markdown("##### 1. Order Setup")
        order_type = st.radio("Order Type", ["dine-in", "takeaway"], horizontal=True)
        
        selected_table_no = "Takeaway"
        covers = 1
        
        if order_type == "dine-in":
            if tables_df.empty:
                st.error("Table data is unavailable.")
            else:
                table_options = [f"Table {row['table_no']} ({row['seats']} Seats - {row['zone']})" for _, row in tables_df.iterrows()]
                selected_table_str = st.selectbox("Select Table", table_options)
                table_idx = table_options.index(selected_table_str)
                table_row = tables_df.iloc[table_idx]
                selected_table_no = str(table_row["table_no"])
                max_seats = int(table_row["seats"])
                
                covers = st.number_input("Number of Guests (Covers)", min_value=1, max_value=20, value=min(2, max_seats))
                
                if covers > max_seats:
                    st.warning(f"Party size of {covers} exceeds Table {selected_table_no}'s capacity of {max_seats} seats. Please select a larger table.")
        else:
            st.info("Takeaway order selected (No service charge will be applied).")

        st.divider()
        st.markdown("##### 2. Add Item to Order Ticket")
        
        # Filter available menu items (must be active, not out of stock, and have a valid price)
        valid_items_df = menu_df[(menu_df["active"] == "yes") & (menu_df["price_aed"].notna()) & (menu_df["price_aed"] > 0)].copy()
        
        if valid_items_df.empty:
            st.warning("No active menu items with valid prices available.")
        else:
            dish_options = [f"{row['dish_id']} - {row['name']} ({row['price_aed']:.2f} AED)" for _, row in valid_items_df.iterrows()]
            selected_dish_str = st.selectbox("Select Menu Item", dish_options)
            dish_idx = dish_options.index(selected_dish_str)
            selected_dish = valid_items_df.iloc[dish_idx]
            
            c_qty, c_kids, c_comp = st.columns([1, 1, 1])
            with c_qty:
                item_qty = st.number_input("Quantity", min_value=1, max_value=20, value=1)
            with c_kids:
                is_kids_eligible = str(selected_dish["kids_friendly"]).lower() == "yes"
                is_kids = st.checkbox("Kids' Portion (Half Price)", disabled=not is_kids_eligible)
                if not is_kids_eligible:
                    st.caption("Not eligible for kids portion")
            with c_comp:
                is_complimentary = st.checkbox("Complimentary Line Item")
                
            comp_reason = ""
            if is_complimentary:
                comp_reason = st.text_input("Manager Reason for Complimentary Item", placeholder="e.g. VIP guest / kitchen delay")
                
            item_note = st.text_input("Special Notes / Instructions", placeholder="e.g. Extra spicy / no onions")
            
            if st.button("➕ Add Item to Ticket"):
                if is_complimentary and not comp_reason.strip():
                    st.error("Please enter a reason for marking the line item as complimentary.")
                else:
                    unit_price = float(selected_dish["price_aed"])
                    if is_kids:
                        unit_price = unit_price / 2.0
                    if is_complimentary:
                        unit_price = 0.0
                        
                    cart_item = {
                        "dish_id": selected_dish["dish_id"],
                        "dish_name": selected_dish["name"],
                        "qty": item_qty,
                        "original_price": float(selected_dish["price_aed"]),
                        "unit_price_aed": unit_price,
                        "is_kids": is_kids,
                        "is_complimentary": is_complimentary,
                        "complimentary_reason": comp_reason.strip(),
                        "note": item_note.strip(),
                        "allergens": selected_dish["allergens"]
                    }
                    st.session_state.order_cart.append(cart_item)
                    st.success(f"Added {item_qty}x {selected_dish['name']} to ticket.")
                    st.rerun()

    with col_order_right:
        st.markdown("##### 🧾 Live Order Ticket")
        
        if not st.session_state.order_cart:
            st.info("Order ticket is currently empty. Add menu items on the left.")
        else:
            cart_data = []
            subtotal = 0.0
            
            for idx, item in enumerate(st.session_state.order_cart):
                line_total = item["unit_price_aed"] * item["qty"]
                subtotal += line_total
                
                type_tag = ""
                if item["is_kids"]:
                    type_tag += " [Kids Portion 50%]"
                if item["is_complimentary"]:
                    type_tag += f" [Complimentary: {item['complimentary_reason']}]"
                    
                cart_data.append({
                    "#": idx + 1,
                    "Item": f"{item['dish_name']}{type_tag}",
                    "Qty": item["qty"],
                    "Unit (AED)": f"{item['unit_price_aed']:.2f}",
                    "Line Total": f"{line_total:.2f} AED"
                })
                
            st.table(pd.DataFrame(cart_data))
            
            if st.button("🗑️ Clear Order Ticket"):
                st.session_state.order_cart = []
                st.rerun()

            # Bill Breakdown Calculations
            service_charge = (subtotal * 0.10) if order_type == "dine-in" else 0.0
            vat = subtotal * 0.05
            total_bill = subtotal + service_charge + vat
            
            st.markdown("""
            <div class="bill-box">
                <h4>Bill Summary</h4>
            """, unsafe_allow_html=True)
            
            st.markdown(f'<div class="bill-line"><span>Food & Drink Subtotal:</span><span><b>{subtotal:.2f} AED</b></span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bill-line"><span>Service Charge (10% Dine-in):</span><span><b>{service_charge:.2f} AED</b></span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bill-line"><span>VAT (5%):</span><span><b>{vat:.2f} AED</b></span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bill-line bill-total"><span>Total Bill:</span><span><b>{total_bill:.2f} AED</b></span></div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("")
            
            if st.button("✅ Confirm & Submit Order"):
                # Generate unique Order ID
                existing_orders = getattr(db, "get_all_orders", lambda: [])()
                next_num = 8001 + len(existing_orders)
                new_order_id = f"O{next_num}"
                
                order_summary = {
                    "order_id": new_order_id,
                    "time_str": datetime.now().strftime("%H:%M"),
                    "table_no": selected_table_no,
                    "type": order_type,
                    "covers": covers,
                    "subtotal": subtotal,
                    "service_charge": service_charge,
                    "vat": vat,
                    "total": total_bill,
                    "status": "new"
                }
                
                success, msg = db.save_order(order_summary, st.session_state.order_cart)
                if success:
                    st.success(f"Order #{new_order_id} successfully saved to database and sent to kitchen!")
                    st.session_state.order_cart = []
                    st.rerun()
                else:
                    st.error(msg)


# ==========================================
# TAB 3: ORDER HISTORY
# ==========================================
with tabs[2]:
    st.subheader("📜 Order History & Saved Records")
    
    order_source = st.radio("Select View", ["App Submitted Orders", "Yesterday's Orders"], horizontal=True)
    
    if order_source == "App Submitted Orders":
        saved_orders = getattr(db, "get_all_orders", lambda: [])()
        if not saved_orders:
            st.info("No orders placed yet. Create an order in the 'Create New Order' tab — it will be saved permanently here!")
        else:
            orders_df = pd.DataFrame(saved_orders)
            st.markdown(f"**Total Persistent App Orders Saved:** {len(orders_df)}")
            
            col_search1, col_search2 = st.columns(2)
            with col_search1:
                search_app_oid = st.text_input("Filter Saved Orders by ID (e.g. O8001)")
            with col_search2:
                filter_app_type = st.selectbox("Filter by Order Type", ["All Types"] + list(orders_df["type"].unique()))
                
            filtered_orders_df = orders_df.copy()
            if search_app_oid.strip():
                filtered_orders_df = filtered_orders_df[filtered_orders_df["order_id"].astype(str).str.contains(search_app_oid.strip(), case=False)]
            if filter_app_type != "All Types":
                filtered_orders_df = filtered_orders_df[filtered_orders_df["type"] == filter_app_type]
                
            st.dataframe(filtered_orders_df, hide_index=True, use_container_width=True)
            
            st.divider()
            selected_oid = st.selectbox("Select Order ID to View Detailed Line Items", filtered_orders_df["order_id"].unique() if not filtered_orders_df.empty else [])
            if selected_oid:
                items = db.get_order_items(selected_oid)
                if items:
                    st.markdown(f"**Itemized Details for Order #{selected_oid}:**")
                    items_df = pd.DataFrame(items)
                    st.dataframe(items_df[["dish_id", "dish_name", "qty", "unit_price_aed", "is_kids", "is_complimentary", "complimentary_reason", "note"]], hide_index=True, use_container_width=True)

    else:
        if yesterday_df.empty:
            st.warning("No historical orders found in dataset.")
        else:
            st.markdown(f"**Total Line Items from Yesterday:** {len(yesterday_df)}")
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                search_order_id = st.text_input("Filter by Order ID (e.g. O8001)")
            with col_f2:
                filter_type = st.selectbox("Filter by Order Type", ["All Types"] + list(yesterday_df["type"].unique()))
                
            filtered_df = yesterday_df.copy()
            if search_order_id.strip():
                filtered_df = filtered_df[filtered_df["order_id"].astype(str).str.contains(search_order_id.strip(), case=False)]
            if filter_type != "All Types":
                filtered_df = filtered_df[filtered_df["type"] == filter_type]
                
            st.dataframe(filtered_df, hide_index=True, use_container_width=True)


# Mandatory Footer
st.markdown('<p class="footer-text">Saffron Court Internal Management App</p>', unsafe_allow_html=True)
