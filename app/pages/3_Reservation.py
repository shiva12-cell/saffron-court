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
    page_title="Reservations — Saffron Court",
    page_icon="📅",
    layout="wide"
)

# Custom High-Contrast Styling
st.markdown("""
<style>
    .page-header {
        color: #8B0000;
        font-family: 'Playfair Display', Georgia, serif;
        margin-bottom: 0.1rem;
    }
    .res-card {
        background-color: #FFFFFF;
        color: #111111 !important;
        border: 1px solid #CCCCCC;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    .res-card h4, .res-card p, .res-card span {
        color: #111111 !important;
        margin-bottom: 0.3rem;
    }
    .clash-badge {
        background-color: #FFCDD2;
        color: #B71C1C !important;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    .dup-badge {
        background-color: #FFE0B2;
        color: #E65100 !important;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    .status-confirmed {
        color: #1976D2 !important;
        font-weight: 600;
    }
    .status-seated {
        color: #388E3C !important;
        font-weight: 600;
    }
    .status-completed {
        color: #616161 !important;
        font-weight: 500;
    }
    .status-cancelled {
        color: #D32F2F !important;
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

st.markdown('<h1 class="page-header">📅 Reservation Management</h1>', unsafe_allow_html=True)
st.caption("Manage table bookings and waitlists.")

# Load Datasets & DB Data safely
tables_df = data_manager.load_tables()
reservations = db.get_all_reservations()
waitlist = db.get_waitlist()

# Create table zone map
table_zone_map = {}
table_seat_map = {}
if not tables_df.empty:
    for _, t in tables_df.iterrows():
        table_zone_map[str(t["table_no"])] = str(t["zone"])
        table_seat_map[str(t["table_no"])] = int(t["seats"])

tabs = st.tabs(["📋 Tonight's Schedule", "➕ New Reservation", "⏳ Walk-in Waitlist"])

# ==========================================
# TAB 1: TONIGHT'S SCHEDULE & DIRECTORY
# ==========================================
with tabs[0]:
    st.subheader("Tonight's Reservation Directory")
    
    if not reservations:
        st.info("No reservations recorded for tonight.")
    else:
        # Filters
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            zones = ["All Zones"] + sorted(list(set(table_zone_map.values())))
            selected_zone = st.selectbox("Filter by Zone", zones)
        with f_col2:
            table_nums = ["All Tables"] + sorted(list(set(str(r["table_no"]) for r in reservations)), key=lambda x: int(x) if x.isdigit() else 99)
            selected_table = st.selectbox("Filter by Table Number", table_nums)
        with f_col3:
            statuses = ["All Statuses", "confirmed", "seated", "completed", "cancelled"]
            selected_status = st.selectbox("Filter by Status", statuses)
            
        filtered_res = []
        for r in reservations:
            t_num = str(r["table_no"])
            t_zone = table_zone_map.get(t_num, "General")
            
            if selected_zone != "All Zones" and t_zone != selected_zone:
                continue
            if selected_table != "All Tables" and t_num != selected_table:
                continue
            if selected_status != "All Statuses" and r.get("status") != selected_status:
                continue
            filtered_res.append(r)
            
        st.markdown(f"**Showing {len(filtered_res)} of {len(reservations)} reservations**")
        st.divider()
        
        for r in filtered_res:
            ref_id = r["ref"]
            t_num = str(r["table_no"])
            t_seats = table_seat_map.get(t_num, 0)
            t_zone = table_zone_map.get(t_num, "Main Dining")
            p_size = int(r["party_size"])
            p_status = str(r["status"]).lower()
            
            # House Rule Checks
            is_clash, clashing_res = db.check_table_clash(t_num, r["time_str"], current_ref=ref_id)
            is_dup, dup_res = db.check_duplicate_phone(r["phone"], current_ref=ref_id)
            is_overcapacity = p_size > t_seats if t_seats > 0 else False
            
            clash_warning = f" <span class='clash-badge'>⚠️ 90-MIN CLASH (with #{clashing_res['ref']} at {clashing_res['time_str']})</span>" if is_clash else ""
            dup_warning = f" <span class='dup-badge'>⚠️ DUPLICATE PHONE (also reserved #{dup_res['ref']} at {dup_res['time_str']})</span>" if is_dup else ""
            capacity_warning = f" <span class='clash-badge'>⚠️ OVERCAPACITY ({p_size} guests for {t_seats}-seat Table)</span>" if is_overcapacity else ""
            
            status_class = f"status-{p_status}" if p_status in ["confirmed", "seated", "completed", "cancelled"] else ""
            notes_str = f" <i>(Notes: {r['notes']})</i>" if r.get("notes") and str(r["notes"]).strip() != "nan" else ""
            
            st.markdown(f"""
            <div class="res-card">
                <h4>Booking #{ref_id} — {r['guest_name']} <span class="{status_class}">[{p_status.upper()}]</span>{clash_warning}{dup_warning}{capacity_warning}</h4>
                <p><b>Time:</b> {r['time_str']} | <b>Table:</b> Table {t_num} ({t_seats} seats - {t_zone}) | <b>Party Size:</b> {p_size} guests | <b>Phone:</b> {r['phone']}{notes_str}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if is_overcapacity:
                rec = db.suggest_best_table(p_size)
                if rec:
                    st.caption(f"💡 **Table Recommendation:** Table {rec['table_no']} ({rec['seats']} seats - {rec['zone']}) is the smallest table that fits {p_size} guests.")

            c_act1, c_act2, c_act3, _ = st.columns([1, 1, 1, 2])
            with c_act1:
                if p_status != "seated" and st.button("🪑 Mark Seated", key=f"seat_{ref_id}"):
                    success, msg = db.update_reservation_status(ref_id, "seated")
                    if success:
                        st.success(msg)
                        st.rerun()
            with c_act2:
                if p_status != "completed" and st.button("✅ Complete", key=f"comp_{ref_id}"):
                    success, msg = db.update_reservation_status(ref_id, "completed")
                    if success:
                        st.success(msg)
                        st.rerun()
            with c_act3:
                if p_status != "cancelled" and st.button("❌ Cancel", key=f"canc_{ref_id}"):
                    success, msg = db.update_reservation_status(ref_id, "cancelled")
                    if success:
                        st.success(msg)
                        st.rerun()
            st.divider()


# ==========================================
# TAB 2: NEW RESERVATION ENGINE
# ==========================================
with tabs[1]:
    st.subheader("➕ Book New Reservation")
    st.caption("Create a new booking for tonight with automatic House Rule validation.")
    
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        g_name = st.text_input("Guest Name", placeholder="e.g. Tariq Al-Mansoor")
        g_phone = st.text_input("Phone Number", placeholder="e.g. +971 50 123 4567")
        g_party = st.number_input("Party Size (Guests)", min_value=1, max_value=20, value=2)
        g_notes = st.text_input("Special Notes / Preferences", placeholder="e.g. Birthday / Window seat please")
        
    with col_r2:
        g_time = st.time_input("Booking Time", datetime.strptime("19:30", "%H:%M").time())
        g_time_str = g_time.strftime("%H:%M")
        
        table_opts = [f"Table {row['table_no']} ({row['seats']} Seats - {row['zone']})" for _, row in tables_df.iterrows()] if not tables_df.empty else []
        selected_table_opt = st.selectbox("Select Table Number", table_opts)
        
        sel_table_no = "1"
        sel_table_seats = 2
        if table_opts and selected_table_opt:
            t_idx = table_opts.index(selected_table_opt)
            t_row = tables_df.iloc[t_idx]
            sel_table_no = str(t_row["table_no"])
            sel_table_seats = int(t_row["seats"])
            
    st.divider()
    st.markdown("##### 🛡️ House Rule Validation Check")
    
    # House Rule Validation Checks
    has_clash, clashing_b = db.check_table_clash(sel_table_no, g_time_str)
    has_dup, dup_b = db.check_duplicate_phone(g_phone)
    is_cap_exceeded = g_party > sel_table_seats
    
    can_submit = True
    
    if is_cap_exceeded:
        rec_table = db.suggest_best_table(g_party)
        rec_msg = f" Suggested table: Table {rec_table['table_no']} ({rec_table['seats']} seats - {rec_table['zone']})." if rec_table else " No larger table available."
        st.error(f"⚠️ **Capacity Violation:** Party size of {g_party} exceeds Table {sel_table_no}'s capacity of {sel_table_seats} seats.{rec_msg}")
        can_submit = False
    else:
        st.success(f"✅ Table {sel_table_no} seat capacity ({sel_table_seats} seats) fits party size of {g_party}.")
        
    if has_clash:
        st.warning(f"⚠️ **90-Minute Booking Clash:** Table {sel_table_no} is held by booking #{clashing_b['ref']} at {clashing_b['time_str']}. Bookings must be at least 90 minutes apart.")
    else:
        st.success(f"✅ 90-Minute Hold Window is clear for Table {sel_table_no} at {g_time_str}.")
        
    if has_dup:
        st.warning(f"⚠️ **Duplicate Phone Booking Alert:** Phone number '{g_phone}' already has an active reservation (#{dup_b['ref']} at {dup_b['time_str']}). The same phone booking twice is one booking.")
        
    st.write("")
    if st.button("✅ Confirm & Save Reservation"):
        if not g_name.strip() or not g_phone.strip():
            st.error("Please enter guest name and phone number.")
        elif not can_submit:
            st.error("Cannot submit booking: Party size exceeds selected table capacity. Please select an appropriately sized table.")
        else:
            # Generate next ref ID (e.g. R5034)
            next_ref_num = 5034 + len(reservations)
            new_ref = f"R{next_ref_num}"
            
            new_res_data = {
                "ref": new_ref,
                "guest_name": g_name.strip(),
                "phone": g_phone.strip(),
                "party_size": g_party,
                "time_str": g_time_str,
                "table_no": sel_table_no,
                "notes": g_notes.strip(),
                "status": "confirmed"
            }
            
            success, msg = db.save_reservation(new_res_data)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


# ==========================================
# TAB 3: WALK-IN WAITLIST
# ==========================================
with tabs[2]:
    st.subheader("⏳ Walk-in Waitlist Management")
    st.caption("Manage walk-in guests arriving without reservations.")
    
    col_w1, col_w2 = st.columns([1, 1])
    
    with col_w1:
        st.markdown("##### Add Walk-in Guest to Waitlist")
        w_name = st.text_input("Guest Name ", placeholder="e.g. Karim Nabil")
        w_phone = st.text_input("Phone Number ", placeholder="e.g. +971 52 987 6543")
        w_party = st.number_input("Party Size ", min_value=1, max_value=20, value=2)
        w_notes = st.text_input("Notes ", placeholder="e.g. Prefers Terrace if available")
        
        if st.button("➕ Add Walk-in to Waitlist"):
            if not w_name.strip():
                st.error("Please enter guest name.")
            else:
                wait_entry = {
                    "guest_name": w_name.strip(),
                    "phone": w_phone.strip(),
                    "party_size": w_party,
                    "arrival_time": datetime.now().strftime("%H:%M"),
                    "status": "waiting",
                    "notes": w_notes.strip()
                }
                success, msg = db.save_waitlist_entry(wait_entry)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with col_w2:
        st.markdown("##### Active Waitlist Queue")
        active_waitlist = [w for w in waitlist if w.get("status") == "waiting"]
        
        if not active_waitlist:
            st.info("No walk-in guests currently waiting.")
        else:
            for w in active_waitlist:
                rec_t = db.suggest_best_table(int(w["party_size"]))
                rec_str = f" | <b>Suggested Table:</b> Table {rec_t['table_no']} ({rec_t['seats']} seats)" if rec_t else ""
                
                st.markdown(f"""
                <div class="res-card">
                    <h4>{w['guest_name']} ({w['party_size']} guests)</h4>
                    <p><b>Arrived:</b> {w['arrival_time']} | <b>Phone:</b> {w['phone']}{rec_str}</p>
                </div>
                """, unsafe_allow_html=True)
                
                c_wact1, c_wact2 = st.columns(2)
                with c_wact1:
                    if st.button(f"🪑 Seat Guest (#{w['id']})", key=f"seat_w_{w['id']}"):
                        success, msg = db.update_waitlist_status(w["id"], "seated")
                        if success:
                            st.success(msg)
                            st.rerun()
                with c_wact2:
                    if st.button(f"❌ Remove (#{w['id']})", key=f"rem_w_{w['id']}"):
                        success, msg = db.update_waitlist_status(w["id"], "cancelled")
                        if success:
                            st.success(msg)
                            st.rerun()
                st.divider()

# Mandatory Footer
st.markdown('<p class="footer-text">Saffron Court Internal Management App</p>', unsafe_allow_html=True)
