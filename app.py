import streamlit as st

st.set_page_config(page_title="BIOLOT Demo", layout="wide")
st.title("BIOLOT - Web Demo")

# Engine import
try:
    from engine import calc_scope12
    st.success("engine import OK")
except Exception as e:
    st.error("engine import FAILED")
    st.code(str(e))
    st.stop()

# Sidebar inputs
st.sidebar.header("Inputs")

electricity_kwh_year = st.sidebar.number_input(
    "Electricity (kWh/year)",
    min_value=0.0,
    value=2500000.0,
    step=100000.0
)

natural_gas_m3_year = st.sidebar.number_in
