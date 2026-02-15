import streamlit as st

st.set_page_config(page_title="BIOLOT", layout="wide")
st.title("BIOLOT - Endüstriyel Çevresel Performans Platformu")

# -------------------------------
# MOTOR IMPORT (MODÜLER YAPI)
# -------------------------------
try:
    from engine import calc_scope12, calc_hvac_savings_simple, calc_water_savings
except Exception as e:


    st.error("Hesap motoru yüklenemedi.")
    st.code(str(e))
    st.stop()

# -------------------------------
# SIDEBAR – GİRDİLER
# -------------------------------
st.sidebar.header("Tesis Parametreleri")

electricity_kwh_year = st.sidebar.number_input(
    "Yıllık Elektrik (kWh)",
    min_value=0.0,
    value=2500000.0
)

natural_gas_m3_year = st.sidebar.number_input(
    "Yıllık Doğalgaz (m3)",
    min_value=0.0,
    value=180000.0
)

area_m2 = st.sidebar.number_input(
    "Toplam Alan (m2)",
    min_value=1.0,
    value=20000.0
)

st.sidebar.divider()

carbon_price = st.sidebar.number_input(
    "Karbon Fiyatı (€/ton)",
    min_value=0.0,
    value=85.5
)

grid_factor = st.sidebar.number_input(
    "Elektrik Emisyon Faktörü (kgCO2/kWh)",
    min_value=0.0,
    value=0.43
)

gas_factor = st.sidebar.number_input(
    "Gaz Emisyon Faktörü (kgCO2/m3)",
    min_value=0.0,
    value=2.0
)

st.sidebar.divider()

delta_t = st.sidebar.number_input(
    "Yeşil Soğutma Etkisi (°C)",
    min_value=0.0,
    value=2.4
)

energy_sensitivity = st.sidebar.number_input(
    "1°C Başına Enerji Azalış Oranı",
    min_value=0.0,
    value=0.04
)

beta = st.sidebar.number_input(
    "Bina Elastikiyet Katsayısı",
    min_value=0.0,
    value=0.5
)

st.sidebar.divider()

water_baseline = st.sidebar.number_input(
    "Referans Su (m3/yıl)",
    min_value=0.0,
    value=12000.0
)

water_actual = st.sidebar.number_input(
    "Mevcut Su (m3/yıl)",
    min_value=0.0,
    value=8000.0
)

pump_kwh_per_m3 = st.sidebar.number_input(
    "Pompa Enerji İndeksi (kWh/m3)",
    min_value=0.0,
    value=0.4
)

# -------------------------------
# HESAPLAMA
# -------------------------------
st.divider()
st.subheader("Analiz Sonuçları")

if st.button("Analizi Başlat", type="primary"):

    karbon = calc_scope12(
        electricity_kwh_year,
        natural_gas_m3_year,
        grid_factor,
        gas_factor,
        carbon_price
    )

    hvac = calc_hvac_savings_simple(
        electricity_kwh_year,
        delta_t,
        energy_sensitivity,
        beta,
        grid_factor,
        carbon_price
    )

    su = calc_water_savings(
        water_baseline,
        water_actual,
        pump_kwh_per_m3,
        grid_factor,
        carbon_price
    )

    scope1 = karbon["scope1_ton"]
    scope2 = karbon["scope2_ton"]
    toplam = karbon["total_ton"]
    risk = karbon["risk_eur"]

    st.subheader("Karbon Göstergeleri")
    k1, k2, k3 = st.columns(3)
    k1.metric("Scope 1 (ton/yıl)", f"{scope1:.2f}")
    k2.metric("Scope 2 (ton/yıl)", f"{scope2:.2f}")
    k3.metric("Toplam Emisyon (ton/yıl)", f"{toplam:.2f}")

    k4 = st.metric("Karbon Riski (€ / yıl)", f"{risk:.0f}")

    st.divider()
    st.subheader("HVAC Etkisi")

    h1, h2, h3 = st.columns(3)
    h1.metric("Enerji Tasarrufu (kWh/yıl)", f"{hvac['saved_kwh']:.0f}")
    h2.metric("Önlenen CO2 (ton/yıl)", f"{hvac['saved_co2_ton']:.2f}")
    h3.metric("Kaçınılan Maliyet (€)", f"{hvac['saved_eur']:.0f}")

    st.divider()
    st.subheader("Su Verimliliği")

    s1, s2, s3 = st.columns(3)
    s1.metric("Tasarruf Edilen Su (m3/yıl)", f"{su['saved_water_m3']:.0f}")
    s2.metric("Pompa Enerji Tasarrufu (kWh/yıl)", f"{su['saved_pump_kwh']:.0f}")
    s3.metric("Kaçınılan Maliyet (€)", f"{su['saved_eur']:.0f}")

    toplam_kwh = hvac["saved_kwh"] + su["saved_pump_kwh"]
    toplam_co2 = hvac["saved_co2_ton"] + su["saved_co2_ton"]
    toplam_euro = hvac["saved_eur"] + su["saved_eur"]

    st.divider()
    st.subheader("Toplam Operasyonel Kazanç")

    t1, t2, t3 = st.columns(3)
    t1.metric("Toplam Enerji Tasarrufu (kWh/yıl)", f"{toplam_kwh:.0f}")
    t2.metric("Toplam Önlenen CO2 (ton/yıl)", f"{toplam_co2:.2f}")
    t3.metric("Toplam Kaçınılan Maliyet (€)", f"{toplam_euro:.0f}")

else:
    st.info("Parametreleri girin ve analizi başlatın.")
