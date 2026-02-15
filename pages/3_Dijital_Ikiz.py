import json
from pathlib import Path
from statistics import mean

import streamlit as st

import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# BIOLOT motor
from engine import run_biolot


st.set_page_config(page_title="BIOLOT | Dijital İkiz", layout="wide")
st.title("Dijital İkiz (2D) — Zonlar • Sensörler • Katmanlar")
st.caption("V1: Zon KPI'ları BIOLOT motor çıktısından türetilir (alan bazlı paylaştırma).")

DATA_DIR = Path("data")
ZONES_PATH = DATA_DIR / "zones.json"
SENSORS_PATH = DATA_DIR / "sensors.json"


def load_json(path: Path):
    if not path.exists():
        return None, f"Dosya bulunamadı: {path.as_posix()}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"JSON okunamadı ({path.as_posix()}): {e}"


zones_data, z_err = load_json(ZONES_PATH)
sensors_data, s_err = load_json(SENSORS_PATH)

if z_err:
    st.error(z_err)
    st.stop()
if s_err:
    st.error(s_err)
    st.stop()

zones = zones_data.get("zones", [])
sensors = sensors_data.get("sensors", [])

if not zones:
    st.error("zones.json içinde 'zones' listesi boş.")
    st.stop()

# -------------------------
# Sidebar controls
# -------------------------
st.sidebar.header("Katmanlar")
show_zones = st.sidebar.checkbox("Zonları göster", value=True)
show_sensors = st.sidebar.checkbox("Sensörleri göster", value=True)
show_heatmap = st.sidebar.checkbox("Isı haritası (sensör sıcaklığı)", value=True)

st.sidebar.divider()
st.sidebar.header("Tesis Parametreleri (BIOLOT Motor)")

# NOSAB demo varsayılanları
electricity_kwh_year = st.sidebar.number_input("Yıllık Elektrik (kWh)", min_value=0.0, value=2500000.0)
natural_gas_m3_year = st.sidebar.number_input("Yıllık Doğalgaz (m3)", min_value=0.0, value=180000.0)

carbon_price = st.sidebar.number_input("Karbon Fiyatı (€/ton)", min_value=0.0, value=85.5)
grid_factor = st.sidebar.number_input("Elektrik Emisyon Faktörü (kgCO2/kWh)", min_value=0.0, value=0.43)
gas_factor = st.sidebar.number_input("Gaz Emisyon Faktörü (kgCO2/m3)", min_value=0.0, value=2.0)

delta_t = st.sidebar.number_input("Yeşil Soğutma Etkisi (°C)", min_value=0.0, value=2.4)
energy_sensitivity = st.sidebar.number_input("1°C Başına Enerji Azalış Oranı", min_value=0.0, value=0.04)
beta = st.sidebar.number_input("Bina Elastikiyet Katsayısı", min_value=0.0, value=0.5)

water_baseline = st.sidebar.number_input("Referans Su (m3/yıl)", min_value=0.0, value=12000.0)
water_actual = st.sidebar.number_input("Mevcut Su (m3/yıl)", min_value=0.0, value=8000.0)
pump_kwh_per_m3 = st.sidebar.number_input("Pompa Enerji İndeksi (kWh/m3)", min_value=0.0, value=0.4)

st.sidebar.divider()
zone_names = [z["name"] for z in zones]
selected_zone_name = st.sidebar.selectbox("Zon seç", zone_names, index=0)
selected_zone = next(z for z in zones if z["name"] == selected_zone_name)

# -------------------------
# Helpers
# -------------------------
def centroid(poly):
    lats = [p[0] for p in poly]
    lons = [p[1] for p in poly]
    return (sum(lats) / len(lats), sum(lons) / len(lons))


# -------------------------
# BIOLOT motor çıktısı
# -------------------------
total_area_m2 = sum(float(z.get("area_m2", 0)) for z in zones)
if total_area_m2 <= 0:
    total_area_m2 = 1.0

# Motor çıktısı (toplam tesis için)
out = run_biolot(
    electricity_kwh_year=electricity_kwh_year,
    natural_gas_m3_year=natural_gas_m3_year,
    area_m2=total_area_m2,
    carbon_price=carbon_price,
    grid_factor=grid_factor,
    gas_factor=gas_factor,
    delta_t=delta_t,
    energy_sensitivity=energy_sensitivity,
    beta=beta,
    water_baseline=water_baseline,
    water_actual=water_actual,
    pump_kwh_per_m3=pump_kwh_per_m3,
)

carbon_total = out["carbon"]
hvac_total = out["hvac"]
water_total = out["water"]
op_total = out["total_operational_gain"]

# Seçili zon payı (alan bazlı)
zone_area = float(selected_zone.get("area_m2", 0))
zone_share = max(0.0, min(1.0, zone_area / total_area_m2))

# Zon KPI: toplamı paylaştır
zone_kpi = {
    "zone_share": zone_share,
    "scope1_ton": carbon_total["scope1_ton"] * zone_share,
    "scope2_ton": carbon_total["scope2_ton"] * zone_share,
    "total_ton": carbon_total["total_ton"] * zone_share,
    "risk_eur": carbon_total["risk_eur"] * zone_share,
    "hvac_saved_kwh": hvac_total["saved_kwh"] * zone_share,
    "hvac_saved_co2_ton": hvac_total["saved_co2_ton"] * zone_share,
    "hvac_saved_eur": hvac_total["saved_eur"] * zone_share,
    "water_saved_m3": water_total["saved_water_m3"] * zone_share,
    "pump_saved_kwh": water_total["saved_pump_kwh"] * zone_share,
    "water_saved_co2_ton": water_total["saved_co2_ton"] * zone_share,
    "water_saved_eur": water_total["saved_eur"] * zone_share,
    "total_saved_kwh": op_total["total_saved_kwh"] * zone_share,
    "total_saved_co2_ton": op_total["total_saved_co2_ton"] * zone_share,
    "total_saved_eur": op_total["total_saved_eur"] * zone_share,
}

# Basit risk flag (demo kuralı)
# temp olmadığı için, risk'i karbon riski €/yıl bazlı normalize ediyoruz (gösterim için)
if zone_kpi["risk_eur"] > 50000:
    risk_flag = "YÜKSEK"
elif zone_kpi["risk_eur"] > 20000:
    risk_flag = "ORTA"
else:
    risk_flag = "DÜŞÜK"

# -------------------------
# Map
# -------------------------
center_lat, center_lon = centroid(selected_zone["polygon"])
m = folium.Map(location=[center_lat, center_lon], zoom_start=17, control_scale=True)

if show_zones:
    zones_fg = folium.FeatureGroup(name="Zonlar", show=True)
    for z in zones:
        poly = z["polygon"]
        color = z.get("style", {}).get("color", "#2E7D32")
        fill_color = z.get("style", {}).get("fillColor", "#66BB6A")
        fill_opacity = z.get("style", {}).get("fillOpacity", 0.25)

        tooltip = f"{z['name']} | Alan: {z.get('area_m2','-')} m²"
        popup = folium.Popup(
            f"<b>{z['name']}</b><br>"
            f"Alan: {z.get('area_m2','-')} m²<br>"
            f"Not: {z.get('note','-')}",
            max_width=350,
        )

        folium.Polygon(
            locations=poly,
            color=color,
            fill=True,
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            weight=3,
            tooltip=tooltip,
            popup=popup,
        ).add_to(zones_fg)

    zones_fg.add_to(m)

zone_id = selected_zone["id"]
zone_sensors = [s for s in sensors if s.get("zone_id") == zone_id]

if show_sensors:
    sens_fg = folium.FeatureGroup(name="Sensörler", show=True)
    for s in sensors:
        lat, lon = s["lat"], s["lon"]
        last = s.get("last", {})
        temp = last.get("temp_c", None)
        rh = last.get("rh_pct", None)
        soil = last.get("soil_moist_pct", None)
        flow = last.get("flow_lpm", None)

        popup_html = (
            f"<b>{s['name']}</b><br>"
            f"Tip: {s.get('type','-')}<br>"
            f"Zon: {s.get('zone_name','-')}<br><br>"
            f"Sıcaklık: {temp if temp is not None else '-'} °C<br>"
            f"Nem: {rh if rh is not None else '-'} %<br>"
            f"Toprak Nem: {soil if soil is not None else '-'} %<br>"
            f"Debi: {flow if flow is not None else '-'} L/dk<br>"
            f"Zaman: {last.get('ts','-')}"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color="#1565C0",
            fill=True,
            fill_color="#1E88E5",
            fill_opacity=0.9,
            tooltip=s["name"],
            popup=folium.Popup(popup_html, max_width=350),
        ).add_to(sens_fg)

    sens_fg.add_to(m)

if show_heatmap:
    heat_points = []
    for s in sensors:
        temp = s.get("last", {}).get("temp_c", None)
        if temp is None:
            continue
        heat_points.append([s["lat"], s["lon"], float(temp)])

    if heat_points:
        hm_fg = folium.FeatureGroup(name="Isı Haritası (Temp)", show=True)
        HeatMap(heat_points, radius=28, blur=20, min_opacity=0.25).add_to(hm_fg)
        hm_fg.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# -------------------------
# Layout
# -------------------------
left, right = st.columns([2, 1], gap="large")

with left:
    st.subheader("Harita")
    st_folium(m, height=620, width=None)

with right:
    st.subheader("Zon Özeti")
    st.write(f"**Zon:** {selected_zone['name']}")
    st.write(f"**Alan:** {selected_zone.get('area_m2','-')} m²")
    st.write(f"**Pay:** %{zone_share*100:.1f}")
    st.write(f"**Risk Seviyesi:** {risk_flag}")

    st.divider()
    st.subheader("Zon KPI (BIOLOT)")

    a1, a2 = st.columns(2)
    a1.metric("Zon Toplam CO2 (t/yıl)", f"{zone_kpi['total_ton']:.2f}")
    a2.metric("Zon Karbon Riski (€)", f"{zone_kpi['risk_eur']:.0f}")

    b1, b2 = st.columns(2)
    b1.metric("Zon HVAC Tasarruf (kWh/yıl)", f"{zone_kpi['hvac_saved_kwh']:.0f}")
    b2.metric("Zon HVAC €", f"{zone_kpi['hvac_saved_eur']:.0f}")

    c1, c2 = st.columns(2)
    c1.metric("Zon Su Tasarruf (m3/yıl)", f"{zone_kpi['water_saved_m3']:.0f}")
    c2.metric("Zon Pompa kWh", f"{zone_kpi['pump_saved_kwh']:.0f}")

    d1, d2 = st.columns(2)
    d1.metric("Zon Toplam kWh", f"{zone_kpi['total_saved_kwh']:.0f}")
    d2.metric("Zon Toplam €", f"{zone_kpi['total_saved_eur']:.0f}")

    st.divider()
    st.subheader("Zon Sensör Özeti")
    if not zone_sensors:
        st.info("Bu zona bağlı sensör yok.")
    else:
        temps = [s.get("last", {}).get("temp_c") for s in zone_sensors if s.get("last", {}).get("temp_c") is not None]
        rhs = [s.get("last", {}).get("rh_pct") for s in zone_sensors if s.get("last", {}).get("rh_pct") is not None]
        soilm = [s.get("last", {}).get("soil_moist_pct") for s in zone_sensors if s.get("last", {}).get("soil_moist_pct") is not None]

        st.write(f"**Sensör sayısı:** {len(zone_sensors)}")
        s1, s2, s3 = st.columns(3)
        s1.metric("Temp ort (°C)", "-" if not temps else f"{mean(temps):.1f}")
        s2.metric("Nem ort (%)", "-" if not rhs else f"{mean(rhs):.0f}")
        s3.metric("Toprak nem ort (%)", "-" if not soilm else f"{mean(soilm):.0f}")

    with st.expander("Denetlenebilir çıktı (motor JSON)"):
        st.json(out)

    with st.expander("Denetlenebilir çıktı (zon KPI hesap)"):
        st.json(zone_kpi)
