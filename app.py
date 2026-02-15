import streamlit as st
from engine import calc_scope12, calc_hvac_savings_simple, calc_water_savings

st.set_page_config(page_title="BIOLOT Demo", layout="wide")

st.title("BIOLOT — Web Demo")

# -------------------------
# SIDEBAR INPUTS
# -------------------------
st.sidebar.header("Girdiler (NOSAB Demo)")

st.sidebar.subheader("Enerji")
electricity_kwh_year = st.sidebar.number_input(
    "Elektrik (kWh/yıl)", min_value=0.0, value=2_500_000.0, step=100_000.0
)
natural_gas_m3_year = st.sidebar.number_input(
    "Doğalgaz (m³/yıl)", min_value=0.0, value=180_000.0, step=10_000.0
)

st.sidebar.divider()

st.sidebar.subheader("Mikroklima / HVAC")
delta_t = st.sidebar.number_input("Yeşil soğutma etkisi ΔT (°C)", min_value=0.0, value=2.4, step=0.1)
energy_sens = st.sidebar.number_input("1°C başına enerji azalımı", min_value=0.0, value=0.04, step=0.005)
beta = st.sidebar.number_input("Beta (bina elastikiyeti)", min_value=0.0, value=0.5, step=0.05)

st.sidebar
