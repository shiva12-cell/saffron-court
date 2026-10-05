import os
import sqlite3
import pandas as pd
from datetime import datetime
import data_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "saffron_court.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database tables and apply migrations if necessary."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Orders Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                time_str TEXT,
                table_no TEXT,
                type TEXT,
                covers INTEGER,
                subtotal REAL,
                service_charge REAL,
                vat REAL,
                total REAL,
                status TEXT DEFAULT 'new',
                cooking_started_at TEXT
            )
        """)
        
        # Migration check: Ensure cooking_started_at column exists
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN cooking_started_at TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        
        # Order Line Items Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                dish_id TEXT,
                dish_name TEXT,
                qty INTEGER,
                unit_price_aed REAL,
                is_kids INTEGER DEFAULT 0,
                is_complimentary INTEGER DEFAULT 0,
                complimentary_reason TEXT,
                note TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (order_id)
            )
        """)
        
        # Inventory Stock Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_stock (
                ingredient_id TEXT PRIMARY KEY,
                name TEXT,
                unit TEXT,
                stock_qty REAL,
                reorder_level REAL
            )
        """)
        
        # Reservations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                ref TEXT PRIMARY KEY,
                guest_name TEXT,
                phone TEXT,
                party_size INTEGER,
                time_str TEXT,
                table_no TEXT,
                notes TEXT,
                status TEXT DEFAULT 'confirmed',
                created_at TEXT
            )
        """)
        
        # Walk-in Waitlist Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guest_name TEXT,
                phone TEXT,
                party_size INTEGER,
                arrival_time TEXT,
                status TEXT DEFAULT 'waiting',
                notes TEXT
            )
        """)
        
        # Staff Members Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                role TEXT,
                hourly_rate_aed REAL,
                max_hours_per_week INTEGER,
                available_days TEXT,
                active INTEGER DEFAULT 1
            )
        """)
        
        # Settings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        conn.commit()
        
        # Seed inventory_stock if empty
        cursor.execute("SELECT COUNT(*) as count FROM inventory_stock")
        row = cursor.fetchone()
        if row and row["count"] == 0:
            inv_df = data_manager.load_inventory()
            if not inv_df.empty:
                for _, inv_row in inv_df.iterrows():
                    cursor.execute("""
                        INSERT INTO inventory_stock (ingredient_id, name, unit, stock_qty, reorder_level)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        inv_row["ingredient_id"],
                        inv_row["name"],
                        inv_row["unit"],
                        float(inv_row["stock_qty"]),
                        float(inv_row["reorder_level"])
                    ))
                conn.commit()
                
        # Seed reservations if empty
        cursor.execute("SELECT COUNT(*) as count FROM reservations")
        row_res = cursor.fetchone()
        if row_res and row_res["count"] == 0:
            res_df = data_manager.load_reservations()
            if not res_df.empty:
                for _, r_row in res_df.iterrows():
                    cursor.execute("""
                        INSERT INTO reservations (ref, guest_name, phone, party_size, time_str, table_no, notes, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(r_row["ref"]),
                        str(r_row["guest_name"]),
                        str(r_row["phone"]),
                        int(r_row["party_size"]),
                        str(r_row["time"]),
                        str(r_row["table_no"]),
                        str(r_row["notes"]),
                        str(r_row["status"]),
                        datetime.now().isoformat()
                    ))
                conn.commit()
                
        # Seed staff_members if empty
        cursor.execute("SELECT COUNT(*) as count FROM staff_members")
        row_staff = cursor.fetchone()
        if row_staff and row_staff["count"] == 0:
            staff_df = data_manager.load_staff()
            if not staff_df.empty:
                for _, s_row in staff_df.iterrows():
                    cursor.execute("""
                        INSERT INTO staff_members (name, role, hourly_rate_aed, max_hours_per_week, available_days, active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        str(s_row["name"]),
                        str(s_row["role"]),
                        float(s_row["hourly_rate_aed"]),
                        int(s_row["max_hours_per_week"]),
                        str(s_row["available_days"]),
                        1
                    ))
                conn.commit()
                
        conn.close()
    except Exception:
        pass

def set_setting(key: str, value: str):
    """Store or update a setting value."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_setting(key: str, default=None):
    """Get setting value by key."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row["value"] if row else default
    except Exception:
        return default

# ==========================================
# STAFF MANAGEMENT FUNCTIONS
# ==========================================
def get_all_staff():
    """Retrieve all staff members from SQLite."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM staff_members WHERE active = 1 ORDER BY id ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []

def save_staff_member(staff_data: dict):
    """Add a new staff member to SQLite."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO staff_members (name, role, hourly_rate_aed, max_hours_per_week, available_days, active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            staff_data["name"],
            staff_data["role"],
            float(staff_data["hourly_rate_aed"]),
            int(staff_data["max_hours_per_week"]),
            staff_data["available_days"]
        ))
        conn.commit()
        conn.close()
        return True, f"Staff member '{staff_data['name']}' successfully added!"
    except Exception as e:
        return False, f"Could not add staff member. Reason: {str(e)}"

def update_staff_member(staff_id: int, staff_data: dict):
    """Update existing staff member details in SQLite."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE staff_members
            SET name = ?, role = ?, hourly_rate_aed = ?, max_hours_per_week = ?, available_days = ?
            WHERE id = ?
        """, (
            staff_data["name"],
            staff_data["role"],
            float(staff_data["hourly_rate_aed"]),
            int(staff_data["max_hours_per_week"]),
            staff_data["available_days"],
            staff_id
        ))
        conn.commit()
        conn.close()
        return True, f"Staff member '{staff_data['name']}' updated!"
    except Exception as e:
        return False, f"Could not update staff member. Reason: {str(e)}"

def delete_staff_member(staff_id: int):
    """Deactivate or remove staff member from SQLite."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE staff_members SET active = 0 WHERE id = ?", (staff_id,))
        conn.commit()
        conn.close()
        return True, "Staff member removed from active roster."
    except Exception as e:
        return False, f"Could not remove staff member. Reason: {str(e)}"

# ==========================================
# CHEF'S SPECIAL CONFIGURATION
# ==========================================
def get_chefs_special_config():
    """Retrieve all custom configuration fields for Chef's Special."""
    old_price = get_setting("chefs_special_price", None)
    default_price = float(old_price) if old_price else 0.0
    return {
        "dish_id": get_setting("cs_dish_id", "M08"),
        "name": get_setting("cs_name", "Chef's Special of the Day"),
        "price_aed": float(get_setting("cs_price", default_price) or 0.0),
        "allergens": get_setting("cs_allergens", "ask"),
        "kids_friendly": get_setting("cs_kids_friendly", "no"),
        "active": get_setting("cs_active", "yes"),
        "ingredients": get_setting("cs_ingredients", "Chef's daily special preparation")
    }

def save_chefs_special_config(config: dict):
    """Save custom configuration fields for Chef's Special."""
    set_setting("cs_dish_id", config.get("dish_id", "M08"))
    set_setting("cs_name", config.get("name", "Chef's Special of the Day"))
    set_setting("cs_price", str(config.get("price_aed", 0.0)))
    set_setting("chefs_special_price", str(config.get("price_aed", 0.0)))
    set_setting("cs_allergens", config.get("allergens", "ask"))
    set_setting("cs_kids_friendly", config.get("kids_friendly", "no"))
    set_setting("cs_active", config.get("active", "yes"))
    set_setting("cs_ingredients", config.get("ingredients", "Chef's daily special preparation"))
    return True, "Chef's Special configuration successfully saved!"

# ==========================================
# RESERVATION FUNCTIONS
# ==========================================
def parse_time_minutes(time_str: str) -> int:
    """Convert HH:MM string into minutes from midnight."""
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0

def check_table_clash(table_no: str, booking_time_str: str, current_ref: str = None):
    """
    House Rule: A table is held for 90 minutes. 
    Returns (is_clash, clashing_reservation_dict) if another booking on the same table is within 90 minutes.
    """
    try:
        all_res = get_all_reservations()
        target_min = parse_time_minutes(booking_time_str)
        
        for res in all_res:
            if res.get("status") in ["cancelled", "completed"]:
                continue
            if current_ref and res.get("ref") == current_ref:
                continue
            if str(res.get("table_no")) == str(table_no):
                existing_min = parse_time_minutes(res.get("time_str"))
                if abs(target_min - existing_min) < 90:
                    return True, res
        return False, None
    except Exception:
        return False, None

def check_duplicate_phone(phone: str, current_ref: str = None):
    """
    House Rule: The same phone number booking twice for the same evening is one booking, not two. Flag it.
    Returns (is_duplicate, existing_reservation_dict)
    """
    try:
        clean_phone = "".join(filter(str.isdigit, str(phone)))
        if not clean_phone:
            return False, None
            
        all_res = get_all_reservations()
        for res in all_res:
            if res.get("status") in ["cancelled", "completed"]:
                continue
            if current_ref and res.get("ref") == current_ref:
                continue
            existing_phone = "".join(filter(str.isdigit, str(res.get("phone"))))
            if existing_phone and existing_phone == clean_phone:
                return True, res
        return False, None
    except Exception:
        return False, None

def suggest_best_table(party_size: int):
    """
    House Rule: Never seat a party larger than the table's seats. Suggest the smallest table that fits.
    """
    try:
        tables_df = data_manager.load_tables()
        if tables_df.empty:
            return None
            
        valid_tables = tables_df[tables_df["seats"] >= party_size].copy()
        if valid_tables.empty:
            return None
            
        valid_tables = valid_tables.sort_values(by=["seats", "table_no"])
        best_table = valid_tables.iloc[0]
        return {
            "table_no": str(best_table["table_no"]),
            "seats": int(best_table["seats"]),
            "zone": str(best_table["zone"])
        }
    except Exception:
        return None

def save_reservation(res_data: dict):
    """Save a new reservation to SQLite."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reservations (ref, guest_name, phone, party_size, time_str, table_no, notes, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res_data["ref"],
            res_data["guest_name"],
            res_data["phone"],
            res_data["party_size"],
            res_data["time_str"],
            res_data["table_no"],
            res_data.get("notes", ""),
            res_data.get("status", "confirmed"),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        return True, f"Reservation #{res_data['ref']} for {res_data['guest_name']} successfully confirmed!"
    except Exception as e:
        return False, f"Could not save reservation. Reason: {str(e)}"

def update_reservation_status(ref: str, new_status: str):
    """Update status of a reservation (confirmed, seated, completed, cancelled)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE reservations SET status = ? WHERE ref = ?", (new_status, ref))
        conn.commit()
        conn.close()
        return True, f"Reservation #{ref} status updated to '{new_status}'."
    except Exception as e:
        return False, f"Could not update reservation status. Reason: {str(e)}"

def get_all_reservations():
    """Retrieve all reservations stored in SQLite."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reservations ORDER BY time_str ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []

# ==========================================
# WAITLIST FUNCTIONS
# ==========================================
def save_waitlist_entry(wait_data: dict):
    """Save walk-in guest to waitlist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO waitlist (guest_name, phone, party_size, arrival_time, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            wait_data["guest_name"],
            wait_data["phone"],
            wait_data["party_size"],
            wait_data.get("arrival_time", datetime.now().strftime("%H:%M")),
            wait_data.get("status", "waiting"),
            wait_data.get("notes", "")
        ))
        conn.commit()
        conn.close()
        return True, f"Walk-in guest '{wait_data['guest_name']}' added to waitlist."
    except Exception as e:
        return False, f"Could not add to waitlist. Reason: {str(e)}"

def update_waitlist_status(wait_id: int, new_status: str):
    """Update waitlist entry status (waiting, seated, cancelled)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE waitlist SET status = ? WHERE id = ?", (new_status, wait_id))
        conn.commit()
        conn.close()
        return True, f"Waitlist entry updated to '{new_status}'."
    except Exception as e:
        return False, f"Could not update waitlist status. Reason: {str(e)}"

def get_waitlist():
    """Retrieve all waitlist entries."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM waitlist ORDER BY id ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []

# ==========================================
# ORDER & INVENTORY FUNCTIONS
# ==========================================
def save_order(order_data: dict, line_items: list):
    """Save new order and its line items to SQLite database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO orders (order_id, time_str, table_no, type, covers, subtotal, service_charge, vat, total, status, cooking_started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_data["order_id"],
            order_data.get("time_str", datetime.now().strftime("%H:%M")),
            order_data["table_no"],
            order_data["type"],
            order_data["covers"],
            order_data["subtotal"],
            order_data["service_charge"],
            order_data["vat"],
            order_data["total"],
            order_data.get("status", "new"),
            None
        ))
        
        for item in line_items:
            cursor.execute("""
                INSERT INTO order_items (order_id, dish_id, dish_name, qty, unit_price_aed, is_kids, is_complimentary, complimentary_reason, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_data["order_id"],
                item["dish_id"],
                item["dish_name"],
                item["qty"],
                item["unit_price_aed"],
                1 if item.get("is_kids") else 0,
                1 if item.get("is_complimentary") else 0,
                item.get("complimentary_reason", ""),
                item.get("note", "")
            ))
            
        conn.commit()
        conn.close()
        return True, "Order successfully saved."
    except Exception as e:
        return False, f"Could not save the order. Error: {str(e)}"

def update_order_status(order_id: str, new_status: str):
    """Update kitchen ticket status and handle stock deduction when served."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check current status
        cursor.execute("SELECT status, cooking_started_at FROM orders WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "Order not found."
            
        current_status = row["status"]
        now_str = datetime.now().isoformat()
        
        if new_status == "cooking" and current_status != "cooking":
            cursor.execute("UPDATE orders SET status = ?, cooking_started_at = ? WHERE order_id = ?", ("cooking", now_str, order_id))
        else:
            cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))
            
        conn.commit()
        
        # Deduct inventory stock if order becomes 'served'
        if new_status == "served" and current_status != "served":
            deduct_order_ingredients(conn, order_id)
            
        conn.close()
        return True, f"Order #{order_id} updated to '{new_status}'."
    except Exception as e:
        return False, f"Failed to update order status. Reason: {str(e)}"

def deduct_order_ingredients(conn, order_id: str):
    """Deduct ingredient quantities from inventory based on recipes with unit conversion."""
    try:
        cursor = conn.cursor()
        
        # Get line items for this order
        cursor.execute("SELECT dish_id, qty FROM order_items WHERE order_id = ?", (order_id,))
        items = cursor.fetchall()
        
        recipes_df = data_manager.load_recipes()
        if recipes_df.empty:
            return
            
        for item in items:
            dish_id = item["dish_id"]
            order_qty = item["qty"]
            
            dish_recipes = recipes_df[recipes_df["dish_id"] == dish_id]
            for _, recipe in dish_recipes.iterrows():
                ing_id = recipe["ingredient_id"]
                req_qty_per_portion = float(recipe["qty_per_portion"])
                rec_unit = str(recipe["unit"]).strip().lower()
                
                # Fetch current inventory stock for this ingredient
                cursor.execute("SELECT stock_qty, unit FROM inventory_stock WHERE ingredient_id = ?", (ing_id,))
                inv_row = cursor.fetchone()
                if not inv_row:
                    continue
                    
                current_stock = float(inv_row["stock_qty"])
                inv_unit = str(inv_row["unit"]).strip().lower()
                
                # Unit conversion
                deduction = req_qty_per_portion * order_qty
                if rec_unit == "g" and inv_unit == "kg":
                    deduction = deduction / 1000.0
                elif rec_unit == "ml" and inv_unit == "l":
                    deduction = deduction / 1000.0
                elif rec_unit == "cl" and inv_unit == "l":
                    deduction = deduction / 100.0
                
                new_stock = max(0.0, current_stock - deduction)
                cursor.execute("UPDATE inventory_stock SET stock_qty = ? WHERE ingredient_id = ?", (new_stock, ing_id))
                
        conn.commit()
    except Exception:
        pass

def update_inventory_stock(ingredient_id: str, name: str, unit: str, stock_qty: float, reorder_level: float):
    """Update or insert ingredient stock level in SQLite database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory_stock (ingredient_id, name, unit, stock_qty, reorder_level)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ingredient_id) DO UPDATE SET
                stock_qty = excluded.stock_qty,
                reorder_level = excluded.reorder_level,
                name = excluded.name,
                unit = excluded.unit
        """, (ingredient_id, name, unit, float(stock_qty), float(reorder_level)))
        conn.commit()
        conn.close()
        return True, f"Stock for '{name}' ({ingredient_id}) updated to {stock_qty:.2f} {unit}."
    except Exception as e:
        return False, f"Failed to update stock. Reason: {str(e)}"

def get_inventory_stock():
    """Retrieve all current inventory stock levels."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_stock ORDER BY ingredient_id ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []

def get_out_of_stock_dishes():
    """Identify dishes whose required ingredient stock cannot cover 1 more portion."""
    try:
        stock_list = get_inventory_stock()
        if not stock_list:
            return []
            
        stock_map = {item["ingredient_id"]: (float(item["stock_qty"]), str(item["unit"]).strip().lower()) for item in stock_list}
        recipes_df = data_manager.load_recipes()
        if recipes_df.empty:
            return []
            
        out_of_stock_dishes = set()
        
        for dish_id, group in recipes_df.groupby("dish_id"):
            for _, recipe in group.iterrows():
                ing_id = recipe["ingredient_id"]
                req_qty = float(recipe["qty_per_portion"])
                rec_unit = str(recipe["unit"]).strip().lower()
                
                if ing_id not in stock_map:
                    continue
                    
                avail_stock, inv_unit = stock_map[ing_id]
                
                needed = req_qty
                if rec_unit == "g" and inv_unit == "kg":
                    needed = req_qty / 1000.0
                elif rec_unit == "ml" and inv_unit == "l":
                    needed = req_qty / 1000.0
                elif rec_unit == "cl" and inv_unit == "l":
                    needed = req_qty / 100.0
                    
                if avail_stock < needed:
                    out_of_stock_dishes.add(dish_id)
                    break
                    
        return list(out_of_stock_dishes)
    except Exception:
        return []

def get_all_orders():
    """Retrieve all orders saved in SQLite."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders ORDER BY order_id DESC")
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders
    except Exception:
        return []

def get_order_items(order_id: str):
    """Retrieve line items for a specific order."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        items = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return items
    except Exception:
        return []

# Initialize DB when module is loaded
init_db()
