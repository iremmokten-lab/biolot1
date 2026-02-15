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
area_m2 = st.sidebar.number_input(
    "Factory area (m2)",
    min_value=1.0,
    value=20000.0
)


st.divider()
st.subheader("Calculation")

run = st.button("Calculate", type="primary")

if run:
    r = calc_scope12(
        electricity_kwh_year=electricity_kwh_year,
        natural_gas_m3_year=natural_gas_m3_year,
        carbon_price_eur_per_ton=carbon_price,
    )

    scope1 = r["scope1_ton"]
    scope2 = r["scope2_ton"]
    total = r["total_ton"]
    risk = r["risk_eur"]

    intensity_energy = total / (electricity_kwh_year / 1000000)
    intensity_area = total / (area_m2 / 1000)

    c1, c2, c3 = st.columns(3)
    c1.metric("Scope 1 (ton/year)", f"{scope1:.2f}")
    c2.metric("Scope 2 (ton/year)", f"{scope2:.2f}")
    c3.metric("Total CO2 (ton/year)", f"{total:.2f}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Carbon risk (EUR/year)", f"{risk:.0f}")
    c5.metric("Emission intensity (t/GWh)", f"{intensity_energy:.2f}")
    c6.metric("Area intensity (t/1000m2)", f"{intensity_area:.2f}")


   scope1 = r["scope1_ton"]
scope2 = r["scope2_ton"]
total = r["total_ton"]
risk = r["risk_eur"]

intensity_energy = total / (electricity_kwh_year / 1_000_000)  # ton per GWh
intensity_area = total / (area_m2 / 1000)  # ton per 1000 m2

c1, c2, c3 = st.columns(3)
c1.metric("Scope 1 (ton/year)", f"{scope1:.2f}")
c2.metric("Scope 2 (ton/year)", f"{scope2:.2f}")
c3.metric("Total CO2 (ton/year)", f"{total:.2f}")

c4, c5, c6 = st.columns(3)
c4.metric("Carbon risk (EUR/year)", f"{risk:.0f}")
c5.metric("Emission intensity (t/GWh)", f"{intensity_energy:.2f}")
c6.metric("Area intensity (t/1000m2)", f"{intensity_area:.2f}")

    st.json(r)
else:
    st.info("Change values on the left and press Calculate.")
