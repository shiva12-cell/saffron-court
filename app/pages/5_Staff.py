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
    page_title="Staff — Saffron Court",
    page_icon="👥",
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
    .staff-card {
        background-color: #FFFFFF;
        color: #111111 !important;
        border: 1px solid #CCCCCC;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    .staff-card h4, .staff-card p {
        color: #111111 !important;
        margin-bottom: 0.3rem;
    }
    .cap-alert {
        background-color: #FFCDD2;
        color: #B71C1C !important;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
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

st.markdown('<h1 class="page-header">👥 Staff Management & Payroll</h1>', unsafe_allow_html=True)
st.caption("Manage team roster and payroll.")

# Load active staff from SQLite
staff_members = getattr(db, "get_all_staff", lambda: [])()

tabs = st.tabs(["📋 Staff Roster", "➕ Add / Edit / Remove Staff", "💰 Weekly Payroll & Hours Cap"])

# ==========================================
# TAB 1: STAFF ROSTER
# ==========================================
with tabs[0]:
    st.subheader("Team Roster Directory")
    
    if not staff_members:
        st.info("No staff members found in roster.")
    else:
        st.markdown(f"**Total Active Team Members:** {len(staff_members)}")
        
        roster_table = []
        for s in staff_members:
            roster_table.append({
                "Staff ID": s["id"],
                "Name": s["name"],
                "Role": s["role"],
                "Hourly Rate (AED)": f"{s['hourly_rate_aed']:.2f} AED",
                "Max Hours / Week": f"{s['max_hours_per_week']} hrs",
                "Available Days": s["available_days"]
            })
        st.dataframe(pd.DataFrame(roster_table), hide_index=True, use_container_width=True)


# ==========================================
# TAB 2: ADD / EDIT / REMOVE STAFF
# ==========================================
with tabs[1]:
    st.subheader("Add, Edit, or Remove Staff Members")
    
    mode = st.radio("Select Action", ["➕ Add New Staff", "✏️ Edit Existing Staff", "🗑️ Remove Staff"], horizontal=True)
    st.divider()
    
    # ACTION 1: ADD STAFF
    if mode.startswith("➕"):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            name_in = st.text_input("Full Name", placeholder="e.g. Tariq Mansoor")
            role_in = st.selectbox("Role", ["Manager", "Head chef", "Chef", "Server", "Host", "Barista", "Sous Chef"])
            rate_in = st.number_input("Hourly Rate (AED)", min_value=10.0, max_value=200.0, value=28.0, step=1.0)
        with col_s2:
            max_hrs_in = st.number_input("Max Hours Per Week Cap", min_value=10, max_value=60, value=48, step=1)
            days_in = st.text_input("Available Days", value="Mon-Sat", placeholder="e.g. Mon-Sat or Tue-Sun")
            
        if st.button("✅ Save New Staff Member"):
            if not name_in.strip():
                st.error("Please enter staff member name.")
            else:
                staff_data = {
                    "name": name_in.strip(),
                    "role": role_in,
                    "hourly_rate_aed": rate_in,
                    "max_hours_per_week": max_hrs_in,
                    "available_days": days_in.strip()
                }
                success, msg = db.save_staff_member(staff_data)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ACTION 2: EDIT STAFF
    elif mode.startswith("✏️"):
        if not staff_members:
            st.warning("No staff members available to edit.")
        else:
            staff_opts = [f"{s['id']} - {s['name']} ({s['role']})" for s in staff_members]
            selected_s_str = st.selectbox("Select Staff Member to Edit", staff_opts)
            s_idx = staff_opts.index(selected_s_str)
            target_staff = staff_members[s_idx]
            
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_name = st.text_input("Full Name", value=target_staff["name"])
                e_role = st.selectbox("Role", ["Manager", "Head chef", "Chef", "Server", "Host", "Barista", "Sous Chef"], index=0)
                e_rate = st.number_input("Hourly Rate (AED)", min_value=10.0, max_value=200.0, value=float(target_staff["hourly_rate_aed"]), step=1.0)
            with col_e2:
                e_max_hrs = st.number_input("Max Hours Per Week Cap", min_value=10, max_value=60, value=int(target_staff["max_hours_per_week"]), step=1)
                e_days = st.text_input("Available Days", value=target_staff["available_days"])
                
            if st.button("💾 Update Staff Details"):
                updated_data = {
                    "name": e_name.strip(),
                    "role": e_role,
                    "hourly_rate_aed": e_rate,
                    "max_hours_per_week": e_max_hrs,
                    "available_days": e_days.strip()
                }
                success, msg = db.update_staff_member(target_staff["id"], updated_data)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ACTION 3: REMOVE STAFF
    else:
        if not staff_members:
            st.warning("No staff members available to remove.")
        else:
            staff_opts = [f"{s['id']} - {s['name']} ({s['role']})" for s in staff_members]
            selected_rem_str = st.selectbox("Select Staff Member to Remove", staff_opts)
            s_idx = staff_opts.index(selected_rem_str)
            target_rem = staff_members[s_idx]
            
            st.warning(f"Are you sure you want to remove **{target_rem['name']}** ({target_rem['role']}) from active roster?")
            if st.button(f"🗑️ Confirm Remove {target_rem['name']}"):
                success, msg = db.delete_staff_member(target_rem["id"])
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


# ==========================================
# TAB 3: WEEKLY PAYROLL & HOURS CAP
# ==========================================
with tabs[2]:
    st.subheader("💰 Weekly Hours & Payroll Calculator")
    st.caption("Input scheduled weekly hours, validate against weekly caps, and compute total payroll.")
    
    if not staff_members:
        st.info("No staff members available for payroll calculation.")
    else:
        # Search bar to filter staff by name at the top
        search_query = st.text_input("🔍 Search Staff by Name:", placeholder="Type a staff member's name (e.g. Tariq, Rania...)...").strip()
        
        filtered_staff = [s for s in staff_members if search_query.lower() in s["name"].lower()]
        
        if not filtered_staff:
            st.warning(f"No staff members found matching '{search_query}'.")
        else:
            payroll_table = []
            total_payroll = 0.0
            total_hours = 0.0
            
            st.markdown("##### Enter Scheduled Hours for this Week:")
            
            cols = st.columns(min(len(filtered_staff), 4))
            for idx, s in enumerate(filtered_staff):
                with cols[idx % 4]:
                    st.markdown(f"**{s['name']}** ({s['role']})")
                    st.caption(f"Rate: {s['hourly_rate_aed']:.2f} AED/hr | Cap: {s['max_hours_per_week']} hrs")
                    
                    s_hours = st.number_input(
                        f"Hours ({s['name']})", 
                        min_value=0.0, 
                        max_value=80.0, 
                        value=float(s['max_hours_per_week']), 
                        step=1.0,
                        key=f"hrs_{s['id']}"
                    )
                    
                    is_exceeded = s_hours > s["max_hours_per_week"]
                    if is_exceeded:
                        st.error(f"⚠️ Exceeds max cap of {s['max_hours_per_week']} hrs!")
                        
                    weekly_pay = s_hours * float(s["hourly_rate_aed"])
                    total_payroll += weekly_pay
                    total_hours += s_hours
                    
                    payroll_table.append({
                        "Staff ID": s["id"],
                        "Name": s["name"],
                        "Role": s["role"],
                        "Hourly Rate (AED)": f"{s['hourly_rate_aed']:.2f}",
                        "Scheduled Hours": f"{s_hours:.1f}",
                        "Max Cap": f"{s['max_hours_per_week']} hrs",
                        "Status": "⚠️ EXCEEDED CAP" if is_exceeded else "OK",
                        "Weekly Pay (AED)": f"{weekly_pay:.2f} AED"
                    })
                    
            st.divider()
            st.markdown("##### 💵 Team Payroll Summary")
            
            pc1, pc2, pc3 = st.columns(3)
            pc1.metric("Active Team Members Shown", len(filtered_staff))
            pc2.metric("Total Scheduled Hours", f"{total_hours:.1f} hrs")
            pc3.metric("Total Estimated Weekly Payroll", f"{total_payroll:.2f} AED")
            
            st.write("")
            st.dataframe(pd.DataFrame(payroll_table), hide_index=True, use_container_width=True)

# Mandatory Footer
st.markdown('<p class="footer-text">Saffron Court Internal Management App</p>', unsafe_allow_html=True)
