import streamlit as st

st.set_page_config(
    page_title="App — Saffron Court Management",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Contrast RMS Styling
st.markdown("""
<style>
    .main-title {
        color: #D97706;
        font-family: 'Playfair Display', Georgia, serif;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .stButton>button {
        background-color: #D97706 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #B45309 !important;
        color: #FFFFFF !important;
        transform: translateY(-1px);
    }
    .footer-text {
        text-align: center;
        color: #64748B;
        font-size: 0.9rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #CBD5E1;
    }
</style>
""", unsafe_allow_html=True)

# Main Title & 5-word Subheading
st.markdown('<h1 class="main-title">🏰 Saffron Court Management App</h1>', unsafe_allow_html=True)
st.caption("Rooftop restaurant operations control hub.")

st.divider()

st.subheader("🏛️ Operations Control Hub")

# Clean Grid Layout using Native Bordered Containers without Sub-descriptions
col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.markdown("### 📋 Menu & Orders")
        st.write("")
        if st.button("Launch Menu & Orders →", key="btn_m1", use_container_width=True):
            st.switch_page("pages/1_Menu_and_Orders.py")

with col2:
    with st.container(border=True):
        st.markdown("### 👨‍🍳 Kitchen Display")
        st.write("")
        if st.button("Launch Kitchen →", key="btn_m2", use_container_width=True):
            st.switch_page("pages/2_Kitchen.py")

with col3:
    with st.container(border=True):
        st.markdown("### 📅 Reservations")
        st.write("")
        if st.button("Launch Reservations →", key="btn_m3", use_container_width=True):
            st.switch_page("pages/3_Reservation.py")

st.write("")
col4, col5 = st.columns(2)

with col4:
    with st.container(border=True):
        st.markdown("### 📦 Inventory")
        st.write("")
        if st.button("Launch Inventory →", key="btn_m4", use_container_width=True):
            st.switch_page("pages/4_Inventory.py")

with col5:
    with st.container(border=True):
        st.markdown("### 👥 Staff & Payroll")
        st.write("")
        if st.button("Launch Staff →", key="btn_m5", use_container_width=True):
            st.switch_page("pages/5_Staff.py")

st.divider()

# Quick Overview Cards
st.subheader("💡 Restaurant Quick Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Location", "Dubai Rooftop")
c2.metric("Total Dining Tables", "14 Tables")
c3.metric("Standard Service Charge", "10% (Dine-in)")

# Footer
st.markdown('<p class="footer-text">Saffron Court Internal Management App</p>', unsafe_allow_html=True)
