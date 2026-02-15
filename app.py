import streamlit as st

st.set_page_config(page_title="BIOLOT Demo", layout="wide")
st.title("BIOLOT — Web Demo")

# 1) engine import testi (hata olursa ekranda gösterir)
try:
    from engine import calc_scope12, calc_hvac_savings_simple, calc_water_savings
    st.success("engine.py import edildi ✅")
except Exception as e:
    st.error("engine.py import edilemedi ❌")
    st.code(str(e))
    st.stop()

# 2) Sidebar inputlar (az)
st.sidebar.header("Girdiler")
electricity_kwh_year = st.sidebar.number_input("Elektrik (kWh/yıl)", min_value=0.0, value=2_500_000.0, step=100_000.0)
natural_gas_m3_year = st.sidebar.number_input("Doğalgaz (m³/yıl)", min_value=0.0, value=180_000.0, step=10
