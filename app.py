import streamlit as st

st.set_page_config(page_title="BIOLOT Demo", layout="wide")
st.title("BIOLOT - Web Demo")

try:
    from engine import calc_scope12
    st.success("engine import OK")
except Exception as e:
    st.error("engine import FAILED")
    st.code(str(e))
    st.stop()

st.sidebar.header("Inputs")

electricity_kwh_year = st.sidebar.number_input("Electricity (kWh/year)", min_value=0.0, value=2500000.0)
natural_gas_m3_year = st.sidebar.number_input("Natural gas (m3/year)", min_value=0.0, value=180000.0)
carbon_price = st.sidebar.number_input("Carbon price (EUR/ton)", min_value=0.0, value=85.5)

st.divider()
st.subheader("Calculation")

run = st.button("Calculate", type="primary")

if run:
    r = calc_scope12(
        electricity_kwh_year=electricity_kwh_year,
        natural_gas_m3_year=natural_gas_m3_year,
        carbon_price_eur_per_ton=carbon_price,
    )

    c1, c2 = st.columns(2)
    c1.metric("Total CO2 (ton/year)", f"{r['total_ton']:.2f}")
    c2.metric("Carbon risk (EUR/year)", f"{r['risk_eur']:.0f}")

    st.json(r)
else:
    st.info("Change values on the left and press Calculate.")
