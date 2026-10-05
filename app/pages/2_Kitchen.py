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
    page_title="Kitchen Display — Saffron Court",
    page_icon="👨‍🍳",
    layout="wide"
)

# Custom High-Contrast Styling (Works seamlessly in both Light & Dark themes)
st.markdown("""
<style>
    .page-header {
        color: #8B0000;
        font-family: 'Playfair Display', Georgia, serif;
        margin-bottom: 0.1rem;
    }
    .ticket-card {
        background-color: #FFFFFF;
        color: #111111 !important;
        border: 1px solid #CCCCCC;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    .ticket-card h4, .ticket-card p, .ticket-card span {
        color: #111111 !important;
        margin-bottom: 0.3rem;
    }
    .ticket-new {
        border-left: 6px solid #1976D2 !important;
    }
    .ticket-cooking {
        border-left: 6px solid #F57C00 !important;
    }
    .ticket-delayed {
        border-left: 6px solid #D32F2F !important;
        background-color: #FFEBEE !important;
    }
    .ticket-delayed h4, .ticket-delayed p {
        color: #7F0000 !important;
    }
    .ticket-ready {
        border-left: 6px solid #388E3C !important;
    }
    .ticket-served {
        border-left: 6px solid #757575 !important;
        background-color: #F5F5F5 !important;
        opacity: 0.85;
    }
    .timer-badge {
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.9rem;
    }
    .timer-normal {
        background-color: #FFF3E0;
        color: #E65100 !important;
    }
    .timer-alert {
        background-color: #FFCDD2;
        color: #B71C1C !important;
        font-size: 0.95rem;
    }
    .allergen-tag {
        color: #D32F2F;
        font-size: 0.85rem;
        font-weight: 600;
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

st.markdown('<h1 class="page-header">👨‍🍳 Kitchen Display System</h1>', unsafe_allow_html=True)
st.caption("Track live tickets and cooking timers.")

# Safe Data Loading
try:
    menu_df = data_manager.load_menu()
    recipes_df = data_manager.load_recipes()
    orders = db.get_all_orders()
except Exception:
    menu_df = pd.DataFrame()
    recipes_df = pd.DataFrame()
    orders = []

# Create allergen mapping dict for quick lookup
allergen_map = {}
if not menu_df.empty:
    for _, r in menu_df.iterrows():
        allergen_map[r["dish_id"]] = str(r["allergens"]).strip() if pd.notna(r["allergens"]) else ""

tabs = st.tabs(["🔥 Active Kitchen Tickets", "📦 Recipe & Stock Status", "📜 Served Tickets"])

# Helper function to compute cooking elapsed minutes
def get_elapsed_minutes(cooking_started_str):
    if not cooking_started_str:
        return 0.0
    try:
        started_time = datetime.fromisoformat(cooking_started_str)
        elapsed_sec = (datetime.now() - started_time).total_seconds()
        return max(0.0, elapsed_sec / 60.0)
    except Exception:
        return 0.0

# Safe function caller for db module
def safe_get_out_of_stock_dishes():
    try:
        fn = getattr(db, "get_out_of_stock_dishes", None)
        if callable(fn):
            return fn()
        return []
    except Exception:
        return []

# ==========================================
# TAB 1: ACTIVE KITCHEN TICKETS
# ==========================================
with tabs[0]:
    st.subheader("Live Kitchen Pipeline")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    
    # Filter orders by status
    new_orders = [o for o in orders if o.get("status") == "new"]
    cooking_orders = [o for o in orders if o.get("status") == "cooking"]
    ready_orders = [o for o in orders if o.get("status") == "ready"]
    
    # Check for any delayed cooking orders
    delayed_count = 0
    for o in cooking_orders:
        if get_elapsed_minutes(o.get("cooking_started_at")) > 25.0:
            delayed_count += 1
            
    if delayed_count > 0:
        st.error(f"⚠️ **Urgent Kitchen Warning:** {delayed_count} ticket(s) in 'Cooking' status exceed the 25-minute threshold!")

    # ------------------------------------------
    # COLUMN 1: NEW TICKETS
    # ------------------------------------------
    with col_t1:
        st.markdown(f"### 📥 New Orders ({len(new_orders)})")
        if not new_orders:
            st.info("No new orders waiting.")
        else:
            for order in new_orders:
                st.markdown(f"""
                <div class="ticket-card ticket-new">
                    <h4>Ticket #{order['order_id']} ({str(order['type']).upper()})</h4>
                    <p><b>Table:</b> {order['table_no']} | <b>Covers:</b> {order['covers']} | <b>Placed:</b> {order['time_str']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Line Items
                items = db.get_order_items(order["order_id"])
                for item in items:
                    allergens = allergen_map.get(item["dish_id"], "")
                    allergen_str = f" <span class='allergen-tag'>[Allergens: {allergens}]</span>" if allergens else ""
                    note_str = f" <i>(Note: {item['note']})</i>" if item.get("note") else ""
                    st.markdown(f"• **{item['qty']}x {item['dish_name']}**{allergen_str}{note_str}", unsafe_allow_html=True)
                    
                if st.button(f"▶️ Start Cooking (#{order['order_id']})", key=f"start_{order['order_id']}"):
                    success, msg = db.update_order_status(order["order_id"], "cooking")
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                st.divider()

    # ------------------------------------------
    # COLUMN 2: COOKING TICKETS
    # ------------------------------------------
    with col_t2:
        st.markdown(f"### 🔥 Cooking ({len(cooking_orders)})")
        if not cooking_orders:
            st.info("No tickets currently cooking.")
        else:
            for order in cooking_orders:
                elapsed_min = get_elapsed_minutes(order.get("cooking_started_at"))
                is_delayed = elapsed_min > 25.0
                
                card_class = "ticket-card ticket-delayed" if is_delayed else "ticket-card ticket-cooking"
                timer_class = "timer-badge timer-alert" if is_delayed else "timer-badge timer-normal"
                alert_text = " ⚠️ DELAYED (>25 MIN)" if is_delayed else ""
                
                st.markdown(f"""
                <div class="{card_class}">
                    <h4>Ticket #{order['order_id']} ({str(order['type']).upper()})</h4>
                    <p><b>Table:</b> {order['table_no']} | <b>Timer:</b> <span class="{timer_class}">{elapsed_min:.1f} mins{alert_text}</span></p>
                </div>
                """, unsafe_allow_html=True)
                
                items = db.get_order_items(order["order_id"])
                for item in items:
                    allergens = allergen_map.get(item["dish_id"], "")
                    allergen_str = f" <span class='allergen-tag'>[Allergens: {allergens}]</span>" if allergens else ""
                    note_str = f" <i>(Note: {item['note']})</i>" if item.get("note") else ""
                    st.markdown(f"• **{item['qty']}x {item['dish_name']}**{allergen_str}{note_str}", unsafe_allow_html=True)
                    
                if st.button(f"✅ Mark Ready (#{order['order_id']})", key=f"ready_{order['order_id']}"):
                    success, msg = db.update_order_status(order["order_id"], "ready")
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                st.divider()

    # ------------------------------------------
    # COLUMN 3: READY TICKETS
    # ------------------------------------------
    with col_t3:
        st.markdown(f"### 🛎️ Ready for Service ({len(ready_orders)})")
        if not ready_orders:
            st.info("No tickets ready for service.")
        else:
            for order in ready_orders:
                st.markdown(f"""
                <div class="ticket-card ticket-ready">
                    <h4>Ticket #{order['order_id']} ({str(order['type']).upper()})</h4>
                    <p><b>Table:</b> {order['table_no']} | <b>Status:</b> Ready to Serve</p>
                </div>
                """, unsafe_allow_html=True)
                
                items = db.get_order_items(order["order_id"])
                for item in items:
                    allergens = allergen_map.get(item["dish_id"], "")
                    allergen_str = f" <span class='allergen-tag'>[Allergens: {allergens}]</span>" if allergens else ""
                    st.markdown(f"• **{item['qty']}x {item['dish_name']}**{allergen_str}", unsafe_allow_html=True)
                    
                if st.button(f"🍽️ Mark Served (#{order['order_id']})", key=f"served_{order['order_id']}"):
                    success, msg = db.update_order_status(order["order_id"], "served")
                    if success:
                        st.success(f"Order #{order['order_id']} served! Ingredient stock automatically deducted.")
                        st.rerun()
                    else:
                        st.error(msg)
                st.divider()


# ==========================================
# TAB 2: RECIPE & STOCK STATUS
# ==========================================
with tabs[1]:
    st.subheader("📦 Recipe & Inventory Stock Status")
    
    # Manager Stock Entry Form
    with st.expander("➕ Inventory Update", expanded=True):
        st.caption("Select an Ingredient ID from the dropdown to automatically populate name, measurement unit, stock quantity, and reorder level.")
        
        stock_items_k = getattr(db, "get_inventory_stock", lambda: [])()
        k_inv_map = {item["ingredient_id"]: item for item in stock_items_k}
        if "I61" not in k_inv_map:
            k_inv_map["I61"] = {"ingredient_id": "I61", "name": "Truffle Oil", "unit": "l", "stock_qty": 2.0, "reorder_level": 0.5}

        k_known_ids = sorted(list(k_inv_map.keys()))
        dropdown_opts_k = [f"{i_id} - {k_inv_map[i_id]['name']}" for i_id in k_known_ids]
        dropdown_opts_k.append("+ Add New Custom Ingredient ID")

        # Find default index for I61 if available
        default_idx_k = 0
        for idx_k, opt_k in enumerate(dropdown_opts_k):
            if opt_k.startswith("I61"):
                default_idx_k = idx_k
                break

        selected_k_choice = st.selectbox("Select Ingredient ID to Update / Restock", dropdown_opts_k, index=default_idx_k)

        if selected_k_choice.startswith("+"):
            k_info = {}
            default_k_id = "I62"
            default_k_name = ""
            default_k_unit = "kg"
            default_k_stock = 10.0
            default_k_reorder = 5.0
        else:
            default_k_id = selected_k_choice.split(" - ")[0].strip()
            k_info = k_inv_map.get(default_k_id, {})
            default_k_name = k_info.get("name", "")
            default_k_unit = k_info.get("unit", "l")
            default_k_stock = float(k_info.get("stock_qty", 2.0))
            default_k_reorder = float(k_info.get("reorder_level", 0.5))

        unit_opts_k = ["l", "kg", "pcs", "g", "ml"]
        u_idx_k = unit_opts_k.index(default_k_unit) if default_k_unit in unit_opts_k else 0

        col_st1, col_st2, col_st3, col_st4, col_st5 = st.columns([1.2, 2, 1, 1.2, 1.2])
        with col_st1:
            ing_id_input = st.text_input("Ingredient ID", value=default_k_id)
        with col_st2:
            ing_name_input = st.text_input("Ingredient Name", value=default_k_name)
        with col_st3:
            ing_unit_input = st.selectbox("Unit", unit_opts_k, index=u_idx_k)
        with col_st4:
            ing_stock_input = st.number_input("Stock Quantity", min_value=0.0, value=default_k_stock, step=0.5)
        with col_st5:
            ing_reorder_input = st.number_input("Reorder Level", min_value=0.0, value=default_k_reorder, step=0.1)
            
        if st.button("💾 Save Ingredient Stock"):
            if not ing_id_input.strip() or not ing_name_input.strip():
                st.error("Please enter a valid Ingredient ID and Name.")
            else:
                success, msg = db.update_inventory_stock(
                    ing_id_input.strip(),
                    ing_name_input.strip(),
                    ing_unit_input.strip(),
                    ing_stock_input,
                    ing_reorder_input
                )
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    
    st.divider()
    
    out_of_stock = safe_get_out_of_stock_dishes()
    if out_of_stock:
        st.error(f"🚫 **Dishes Automatically Marked Unavailable due to Depleted Stock ({len(out_of_stock)}):** {', '.join(out_of_stock)}")
    else:
        st.success("✅ All active menu dishes currently have sufficient ingredient stock for at least 1 portion.")
        
    st.divider()
    
    st.markdown("#### Live Ingredient Inventory Stock Table")
    stock_items = getattr(db, "get_inventory_stock", lambda: [])()
    
    if not stock_items:
        st.warning("No inventory stock items found.")
    else:
        inv_table = []
        for item in stock_items:
            is_low = float(item["stock_qty"]) <= float(item["reorder_level"])
            inv_table.append({
                "Ingredient ID": item["ingredient_id"],
                "Name": item["name"],
                "Current Stock": f"{item['stock_qty']:.2f} {item['unit']}",
                "Reorder Level": f"{item['reorder_level']:.2f} {item['unit']}",
                "Status": "⚠️ LOW STOCK" if is_low else "OK"
            })
            
        st.dataframe(pd.DataFrame(inv_table), hide_index=True, use_container_width=True)


# ==========================================
# TAB 3: SERVED TICKETS
# ==========================================
with tabs[2]:
    st.subheader("📜 Completed & Served Tickets")
    served_orders = [o for o in orders if o.get("status") == "served"]
    
    if not served_orders:
        st.info("No served tickets recorded in current session.")
    else:
        st.dataframe(pd.DataFrame(served_orders), hide_index=True, use_container_width=True)

# Mandatory Footer
st.markdown('<p class="footer-text">Saffron Court Internal Management App</p>', unsafe_allow_html=True)
