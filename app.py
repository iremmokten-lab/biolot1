import streamlit as st
from engine import calc_scope12, calc_hvac_savings_simple, calc_water_savings

st.set_page_config(page_title="BIOLOT Demo", layout="wide")
st.title("BIOLOT — Web Demo")

st.sidebar.header("Girdiler (NOSAB Demo)")
area_m2 = st.sidebar.number_input("Fabrika alanı (m²)", min_value=0.0, value=20000.0, step=1000.0)

electricity_kwh_year = st.sidebar.number_input("Elektrik (kWh/yıl)", min_value=0.0, value=2_500_000.0, step=100_000.0)
natural_gas_m3_year = st.sidebar.number_input("Doğalgaz (m³/yıl)", min_value=0.0, value=180_000.0, step=10_000.0)

st.sidebar.divider()
st.sidebar.subheader("Mikroklima / HVAC")
delta_t = st.sidebar.number_input("Yeşil soğutma etkisi ΔT (°C)", min_value=0.0, value=2.4, step=0.1)
energy_sens = st.sidebar.number_input("1°C başına enerji azalımı", min_value=0.0, value=0.04, step=0.005, help="0.04 = %4")
beta = st.sidebar.number_input("Beta (bina elastikiyeti)", min_value=0.0, value=0.5, step=0.05)

st.sidebar.divider()
st.sidebar.subheader("Su / Pompa")
water_baseline = st.sidebar.number_input("Baseline su (m³/yıl)", min_value=0.0, value=12000.0, step=500.0)
water_actual = st.sidebar.number_input("Actual su (m³/yıl)", min_value=0.0, value=8000.0, step=500.0)
pump_kwh_per_m3 = st.sidebar.number_input("Pompa enerji indeksi (kWh/m³)", min_value=0.0, value=0.4, step=0.05)

st.sidebar.divider()
st.sidebar.subheader("Faktörler / Fiyat")
grid_factor = st.sidebar.number_input("Şebeke emisyon faktörü (kgCO₂/kWh)", min_value=0.0, value=0.43, step=0.01)
gas_factor = st.sidebar.number_input("Gaz emisyon faktörü (kgCO₂/m³)", min_value=0.0, value=2.0, step=0.1)
carbon_price = st.sidebar.number_input("Karbon fiyatı (€/tCO₂)", min_value=0.0, value=85.5, step=1.0)

run = st.button("Hesapla", type="primary")

if run:
    scope = calc_scope12(
        electricity_kwh_year=electricity_kwh_year,
        natural_gas_m3_year=natural_gas_m3_year,
        grid_factor_kg_per_kwh=grid_factor,
        gas_factor_kg_per_m3=gas_factor,
        carbon_price_eur_per_ton=carbon_price,
    )

    hvac = calc_hvac_savings_simple(
        electricity_kwh_year=electricity_kwh_year,
        delta_t_c=delta_t,
        energy_sensitivity_per_c=energy_sens,
        beta=beta,
        grid_factor_kg_per_kwh=grid_factor,
        carbon_price_eur_per_ton=carbon_price,
    )

    water = calc_water_savings(
        water_baseline_m3_year=water_baseline,
        water_actual_m3_year=water_actual,
        pump_kwh_per_m3=pump_kwh_per_m3,
        grid_factor_kg_per_kwh=grid_factor,
        carbon_price_eur_per_ton=carbon_price,
    )

    st.subheader("Özet")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scope 1+2 (tCO₂/yıl)", f"{scope['total_ton']:.2f}")
    c2.metric("Karbon riski (€/yıl)", f"{scope['risk_eur']:.0f}")
    c3.metric("HVAC tasarrufu (kWh/yıl)", f"{hvac['saved_kwh']:.0f}")
    c4.metric("Su+Pompa kazancı (€/yıl)", f"{water['saved_eur']:.0f}")

    st.divider()
    st.subheader("Detaylar")
    st.write("**Tesis alanı (m²):**", area_m2)

    colA, colB, colC = st.columns(3)
    colA.json(scope)
    colB.json(hvac)
    colC.json(water)

    st.divider()
    st.subheader("Toplam Operasyonel Kazanç (HVAC + Pompa)")
    total_saved_kwh = hvac["saved_kwh"] + water["saved_pump_kwh"]
    total_saved_co2_ton = hvac["saved_co2_ton"] + water["saved_co2_ton"]
    total_saved_eur = hvac["saved_eur"] + water["saved_eur"]

    k1, k2, k3 = st.columns(3)
    k1.metric("Toplam tasarruf (kWh/yıl)", f"{total_saved_kwh:.0f}")
    k2.metric("Kaçınılan CO₂ (ton/yıl)", f"{total_saved_co2_ton:.3f}")
    k3.metric("Kaçınılan maliyet (€/yıl)", f"{total_saved_eur:.0f}")
