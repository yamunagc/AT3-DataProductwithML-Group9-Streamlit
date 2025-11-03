import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from students.tung import XRPDashboard
from students.vandoan import TRONDashboard
from students.monika import ETHDashboard

st.set_page_config(page_title="Team Crypto Workspace", layout="wide")

# ---- Title ----
st.title("⭐ Group 9 Crypto Prediction")

# ---- Team Tabs (others fill theirs later) ----
tabs = st.tabs(["Tung (XRP)", "Yamuna (BTC)", "Monika (ETH)", "Thang (TRX)"])

with tabs[0]:
    st.write("You are working on **XRP**.")
    xrp = XRPDashboard()
    xrp.run()

with tabs[1]:
    st.write("You are working on **BTC**.")

with tabs[2]:
    st.write("You are working on **ETH**.")
    eth = ETHDashboard()
    eth.run()

with tabs[3]:
    st.write("You are working on **TRON**.")
    tron = TRONDashboard()
    tron.run()
