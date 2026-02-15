import streamlit as st

st.set_page_config(page_title="BIOLOT Demo", layout="wide")
st.title("BIOLOT - Web Demo")

# ---- import engine
try:
    from engine import calc_scope12, calc_hvac_savings_simple, calc_water_savings
    st.success("engine import OK")
except Exception as e:
    st.error("engine import FAILED")
    st.code(str(e))
    st.stop()

# ---- inputs
st.sidebar.header("Inputs")

st.sidebar.subheader("Energy")
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

st.sidebar.divider()
st.sidebar.subheader("Carbon settings")

carbon_price = st.sidebar.number_input(
    "Carbon price (EUR/ton)",
    min_value=0.0,
    value=85.5
)

grid_factor = st.sidebar.number_input(
    "Grid factor (kgCO2/kWh)",
    min_value=0.0,
    value=0.43
)

gas_factor = st.sidebar.number_input(
    "Gas factor (kgCO2/m3)",
    min_value=0.0,
    value=2.0
)

st.sidebar.divider()
st.sidebar.subheader("Facility")

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

st.sidebar.divider()
st.sidebar.subheader("Water / Pump")

water_baseline = st.sidebar.number_input(
    "Water baseline (m3/year)",
    min_value=0.0,
    value=12000.0
)

water_actual = st.sidebar.number_input(
    "Water actual (m3/year)",
    min_value=0.0,
    value=8000.0
)

pump_kwh_per_m3 = st.sidebar.number_input(
    "Pump energy index (kWh/m3)",
    min_value=0.0,
    value=0.4
)

st.divider()
st.subheader("Calculation")

run = st.button("Calculate", type="primary")

if run:
    # --- carbon
    r = calc_scope12(
        electricity_kwh_year=electricity_kwh_year,
        natural_gas_m3_year=natural_gas_m3_year,
        grid_factor_kg_per_kwh=grid_factor,
        gas_factor_kg_per_m3=gas_factor,
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
        grid_factor_kg_per_kwh=grid_factor,
        carbon_price_eur_per_ton=carbon_price,
    )

    st.divider()
    st.subheader("HVAC Impact")

    h1, h2, h3 = st.columns(3)
    h1.metric("HVAC saving (kWh/yr)", f"{hvac['saved_kwh']:.0f}")
    h2.metric("Avoided CO2 (ton/yr)", f"{hvac['saved_co2_ton']:.2f}")
    h3.metric("Avoided cost (EUR/yr)", f"{hvac['saved_eur']:.0f}")

    # --- water
    water = calc_water_savings(
        water_baseline_m3_year=water_baseline,
        water_actual_m3_year=water_actual,
        pump_kwh_per_m3=pump_kwh_per_m3,
        grid_factor_kg_per_kwh=grid_factor,
        carbon_price_eur_per_ton=carbon_price,
    )

    st.divider()
    st.subheader("Water & Pump Impact")

    w1, w2, w3 = st.columns(3)
    w1.metric("Saved water (m3/yr)", f"{water['saved_water_m3']:.0f}")
    w2.metric("Pump saving (kWh/yr)", f"{water['saved_pump_kwh']:.0f}")
    w3.metric("Avoided cost (EUR/yr)", f"{water['saved_eur']:.0f}")

    # --- total operational gain (HVAC + Pump)
    total_saved_kwh = hvac["saved_kwh"] + water["saved_pump_kwh"]
    total_saved_co2_ton = hvac["saved_co2_ton"] + water["saved_co2_ton"]
    total_saved_eur = hvac["saved_eur"] + water["saved_eur"]

    st.divider()
    st.subheader("Total Operational Gain (HVAC + Pump)")

    t1, t2, t3 = st.columns(3)
    t1.metric("Total saving (kWh/yr)", f"{total_saved_kwh:.0f}")
    t2.metric("Total avoided CO2 (ton/yr)", f"{total_saved_co2_ton:.2f}")
    t3.metric("Total avoided cost (EUR/yr)", f"{total_saved_eur:.0f}")

    st.divider()
    st.subheader("Raw results")
    colA, colB, colC = st.columns(3)
    colA.json(r)
    colB.json(hvac)
    colC.json(water)

else:
    st.info("Change values on the left and press Calculate.")
