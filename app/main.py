import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from students.tung import XRPDashboard  
from students.yamuna import BTCDashboard

st.set_page_config(page_title="Team Crypto Workspace", layout="wide")

# ---- Title ----
st.title("⭐ Group 9 Crypto Prediction")

# ---- Team Tabs (others fill theirs later) ----
tabs = st.tabs(["Tung (XRP)", "Yamuna (BTC)", "Monika (ETH)", "Thang (TRX)"])

with tabs[0]:
    st.write("Tung is working on **XRP**.")
    XRPDashboard("XRP").run()

with tabs[1]:
    st.write("Yamuna is working on **BTC**.")
    BTCDashboard("Yamuna").run()

with tabs[2]:
    st.info("👤 Member 2 works on **ETH** — (their module will run here).")

with tabs[3]:
    st.info("👤 Member 3 works on **TRX** — (their module will run here).")
