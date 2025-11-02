import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from students.tung import XRPDashboard
from students.vandoan import TRONDashboard

st.set_page_config(page_title="Team Crypto Workspace", layout="wide")

# ---- Title ----
st.title("⭐ Group 9 Crypto Prediction")

# ---- Team Tabs (others fill theirs later) ----
tabs = st.tabs(["Tung (XRP)", "Monika (BTC)", "Yamuna (ETH)", "Thang (TRX)"])

with tabs[0]:
    st.write("You are working on **XRP**.")
    XRPDashboard("XRP").run()

with tabs[1]:
    st.info("👤 Member 1 works on **BTC** — (their module will run here).")

with tabs[2]:
    st.info("👤 Member 2 works on **ETH** — (their module will run here).")

with tabs[3]:
    st.write("You are working on **XRP**.")
    app = TRONDashboard()
    app.run()
    st.info("👤 Member 3 works on **TRX** — (their module will run here).")
