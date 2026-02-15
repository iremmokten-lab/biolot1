import json
from pathlib import Path
from statistics import mean

import streamlit as st

# Harita için
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium


st.set_page_config(page_title="BIOLOT | Dijital İkiz", layout="wide")
st.title("Dijital İkiz (2D) — Zonlar • Sensörler • Katmanlar")
st.caption("V0: Demo seviyesinde 2D katmanlı dijital ikiz (harita + zon + sensör + basit KPI).")


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

# --- Sidebar controls
st.sidebar.header("Katmanlar")
show_zones = st.sidebar.checkbox("Zonları göster", value=True)
show_sensors = st.sidebar.checkbox("Sensörleri göster", value=True)
show_heatmap = st.sidebar.checkbox("Isı haritası (sensör sıcaklığı)", value=True)

st.sidebar.divider()
zone_names = [z["name"] for z in zones]
selected_zone_name = st.sidebar.selectbox("Zon seç", zone_names, index=0)
selected_zone = next(z for z in zones if z["name"] == selected_zone_name)

# --- Map center
def centroid(poly):
    lats = [p[0] for p in poly]
    lons = [p[1] for p in poly]
    return (sum(lats) / len(lats), sum(lons) / len(lons))

center_lat, center_lon = centroid(selected_zone["polygon"])

# --- Create folium map
m = folium.Map(location=[center_lat, center_lon], zoom_start=17, control_scale=True)

# --- Zones layer
if show_zones:
    zones_fg = folium.FeatureGroup(name="Zonlar", show=True)

    for z in zones:
        poly = z["polygon"]
        color = z.get("style", {}).get("color", "#2E7D32")  # default green
        fill_color = z.get("style", {}).get("fillColor", "#66BB6A")
        fill_opacity = z.get("style", {}).get("fillOpacity", 0.25)

        tooltip = f"{z['name']} | Alan: {z.get('area_m2', '-') } m²"
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

# --- Sensors layer
zone_id = selected_zone["id"]
zone_sensors = [s for s in sensors if s.get("zone_id") == zone_id]

if show_sensors:
    sens_fg = folium.FeatureGroup(name="Sensörler", show=True)

    for s in sensors:
        lat, lon = s["lat"], s["lon"]
        last = s.get("last", {})

        # küçük özet
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

# --- Heatmap layer (temperature)
if show_heatmap:
    heat_points = []
    for s in sensors:
        temp = s.get("last", {}).get("temp_c", None)
        if temp is None:
            continue
        # folium heatmap: [lat, lon, weight]
        heat_points.append([s["lat"], s["lon"], float(temp)])

    if heat_points:
        hm_fg = folium.FeatureGroup(name="Isı Haritası (Temp)", show=True)
        HeatMap(heat_points, radius=28, blur=20, min_opacity=0.25).add_to(hm_fg)
        hm_fg.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# --- Layout: Map + Right panel
left, right = st.columns([2, 1], gap="large")

with left:
    st.subheader("Harita")
    st_folium(m, height=620, width=None)

with right:
    st.subheader("Zon Özeti")
    st.write(f"**Zon:** {selected_zone['name']}")
    st.write(f"**Alan:** {selected_zone.get('area_m2','-')} m²")
    st.write(f"**Not:** {selected_zone.get('note','-')}")

    # Zon KPI (demo)
    kpis = selected_zone.get("kpis", {})
    temp_avg = kpis.get("temp_avg_c", None)
    water_m3_day = kpis.get("water_m3_day", None)
    risk_flag = kpis.get("risk_flag", "NORMAL")

    st.divider()
    st.subheader("Zon KPI (Demo)")

    c1, c2, c3 = st.columns(3)
    c1.metric("Ortalama Sıcaklık (°C)", "-" if temp_avg is None else f"{temp_avg:.1f}")
    c2.metric("Günlük Su (m³/gün)", "-" if water_m3_day is None else f"{water_m3_day:.1f}")
    c3.metric("Risk", str(risk_flag))

    # Sensör özetleri
    st.divider()
    st.subheader("Zon Sensörleri")

    if not zone_sensors:
        st.info("Bu zona bağlı sensör yok (demo verisini sensors.json’dan bağlayabilirsin).")
    else:
        temps = [s.get("last", {}).get("temp_c") for s in zone_sensors if s.get("last", {}).get("temp_c") is not None]
        rhs = [s.get("last", {}).get("rh_pct") for s in zone_sensors if s.get("last", {}).get("rh_pct") is not None]
        soilm = [s.get("last", {}).get("soil_moist_pct") for s in zone_sensors if s.get("last", {}).get("soil_moist_pct") is not None]

        st.write(f"**Sensör sayısı:** {len(zone_sensors)}")
        s1, s2, s3 = st.columns(3)
        s1.metric("Temp ort (°C)", "-" if not temps else f"{mean(temps):.1f}")
        s2.metric("Nem ort (%)", "-" if not rhs else f"{mean(rhs):.0f}")
        s3.metric("Toprak nem ort (%)", "-" if not soilm else f"{mean(soilm):.0f}")

        with st.expander("Sensör listesi"):
            st.json(zone_sensors)
