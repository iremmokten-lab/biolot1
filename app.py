import streamlit as st

st.set_page_config(page_title="BIOLOT Demo", layout="wide")
st.title("BIOLOT - Web Demo")

# ---- import engine
try:
    from engine import calc_scope12, calc_hvac_savings_simple
    st.success("engine import OK")
except Exception as e:
    st.error("engine import FAILED")
    st.code(str(e))
    st.stop()

# ---- inputs
st.sidebar.header("Inputs")

electricity_kwh_year = st.sidebar.number_input(
    "Electricity (kWh/year)",
    min_value=0.0,
    value=2500000.0
)

natural_gas_m3_year = st.sidebar.number_input(
    "Natural gas (m3/year)",
    min_value=0.0,
    value=180000.0
)

carbon_price = st.sidebar.number_input(
    "Carbon price (EUR/ton)",
    min_value=0.0,
    value=85.5
)

area_m2 = st.sidebar.number_input(
    "Factory area (m2)",
    min_value=1.0,
    value=20000.0
)

st.sidebar.divider()
st.sidebar.subheader("HVAC / Microclimate")

delta_t = st.sidebar.number_input(
    "Cooling effect delta T (C)",
    min_value=0.0,
    value=2.4
)

energy_sensitivity = st.sidebar.number_input(
    "Energy sensitivity per C (0.04 = 4%)",
    min_value=0.0,
    value=0.04
)

beta = st.sidebar.number_input(
    "Building elasticity beta",
    min_value=0.0,
    value=0.5
)

st.divider()
st.subheader("Calculation")

run = st.button("Calculate", type="primary")

if run:
    # --- carbon
    r = calc_scope12(
        electricity_kwh_year=electricity_kwh_year,
        natural_gas_m3_year=natural_gas_m3_year,
        carbon_price_eur_per_ton=carbon_price,
    )

    scope1 = r["scope1_ton"]
    scope2 = r["scope2_ton"]
    total = r["total_ton"]
    risk = r["risk_eur"]

    # --- intensity metrics
    if electricity_kwh_year > 0:
        intensity_energy = total / (electricity_kwh_year / 1000000.0)  # t/GWh
    else:
        intensity_energy = 0.0

    intensity_area = total / (area_m2 / 1000.0)  # t per 1000 m2

    st.subheader("Carbon KPIs")

    c1, c2, c3 = st.columns(3)
    c1.metric("Scope 1 (tCO2/yr)", f"{scope1:.2f}")
    c2.metric("Scope 2 (tCO2/yr)", f"{scope2:.2f}")
    c3.metric("Total (tCO2/yr)", f"{total:.2f}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Carbon risk (EUR/yr)", f"{risk:.0f}")
    c5.metric("Intensity (t/GWh)", f"{intensity_energy:.2f}")
    c6.metric("Area intensity (t/1000m2)", f"{intensity_area:.2f}")

    # --- hvac
    hvac = calc_hvac_savings_simple(
        electricity_kwh_year=electricity_kwh_year,
        delta_t_c=delta_t,
        energy_sensitivity_per_c=energy_sensitivity,
        beta=beta,
    )

    st.divider()
    st.subheader("HVAC Impact")

    h1, h2, h3 = st.columns(3)
    h1.metric("HVAC saving (kWh/yr)", f"{hvac['saved_kwh']:.0f}")
    h2.metric("Avoided CO2 (ton/yr)", f"{hvac['saved_co2_ton']:.2f}")
    h3.metric("Avoided cost (EUR/yr)", f"{hvac['saved_eur']:.0f}")

    st.divider()
    st.subheader("Raw results")
    colA, colB = st.columns(2)
    colA.json(r)
    colB.json(hvac)

else:
    st.info("Change values on the left and press Calculate.")
