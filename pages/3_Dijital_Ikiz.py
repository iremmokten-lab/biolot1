import json
import base64
from pathlib import Path

import streamlit as st

# Harita modu
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# Plan modu
from PIL import Image
import plotly.graph_objects as go

# BIOLOT motor
from engine import run_biolot

st.set_page_config(page_title="BIOLOT | Dijital İkiz", layout="wide")
st.title("Dijital İkiz (2D) — Zonlar • Sensörler • Katmanlar")
st.caption("Harita Modu (Leaflet) + Tesis Planı Modu (uydu/plan görseli üstü)")

DATA_DIR = Path("data")
ZONES_PATH = DATA_DIR / "zones.json"
SENSORS_PATH = DATA_DIR / "sensors.json"

PLAN_IMG_PNG = Path("assets/site_plan.png")
PLAN_IMG_JPG = Path("assets/site_plan.jpg")


# -------------------------------
# Helpers
# -------------------------------
def load_json(path: Path):
    if not path.exists():
        st.error(f"Dosya bulunamadı: {path.as_posix()}")
        st.stop()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        st.error(f"JSON okunamadı ({path.as_posix()}): {e}")
        st.stop()


def centroid_latlon(poly):
    lats = [p[0] for p in poly]
    lons = [p[1] for p in poly]
    return (sum(lats) / len(lats), sum(lons) / len(lons))


def load_plan_image_path():
    if PLAN_IMG_PNG.exists():
        return PLAN_IMG_PNG.as_posix()
    if PLAN_IMG_JPG.exists():
        return PLAN_IMG_JPG.as_posix()
    return None


def image_to_data_uri(img_path: str) -> str:
    p = Path(img_path)
    b = p.read_bytes()
    ext = p.suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64," + base64.b64encode(b).decode("utf-8")


def clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def clamp_point_xy(x: float, y: float, width: float, height: float):
    # x: 0..width, y: 0..height
    return clamp(x, 0, width), clamp(y, 0, height)


# -------------------------------
# Load data
# -------------------------------
zones_data = load_json(ZONES_PATH)
sensors_data = load_json(SENSORS_PATH)

zones = zones_data.get("zones", [])
sensors = sensors_data.get("sensors", [])

if not zones:
    st.error("zones.json içinde 'zones' listesi boş.")
    st.stop()

# ---------------- Sidebar ----------------
st.sidebar.header("Mod")
view_mode = st.sidebar.radio("Mod seç", ["Harita Modu", "Tesis Planı Modu"], index=0)

st.sidebar.divider()
st.sidebar.header("Katmanlar")
show_zones = st.sidebar.checkbox("Zonları göster", value=True)
show_sensors = st.sidebar.checkbox("Sensörleri göster", value=True)
show_heatmap = st.sidebar.checkbox("Isı haritası (sensör sıcaklığı)", value=True)

st.sidebar.divider()
st.sidebar.header("Tesis Parametreleri (BIOLOT Motor)")
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
zone_names = [z.get("name", "Zon") for z in zones]
selected_zone_name = st.sidebar.selectbox("Zon seç", zone_names, index=0)
selected_zone = next(z for z in zones if z.get("name") == selected_zone_name)

# ---------------- Engine + KPI ----------------
total_area_m2 = sum(float(z.get("area_m2", 0)) for z in zones) or 1.0

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

zone_area = float(selected_zone.get("area_m2", 0))
zone_share = max(0.0, min(1.0, zone_area / total_area_m2))

zone_kpi = {
    "total_ton": carbon_total["total_ton"] * zone_share,
    "risk_eur": carbon_total["risk_eur"] * zone_share,
    "hvac_saved_kwh": hvac_total["saved_kwh"] * zone_share,
    "hvac_saved_eur": hvac_total["saved_eur"] * zone_share,
    "water_saved_m3": water_total["saved_water_m3"] * zone_share,
    "pump_saved_kwh": water_total["saved_pump_kwh"] * zone_share,
    "total_saved_kwh": op_total["total_saved_kwh"] * zone_share,
    "total_saved_eur": op_total["total_saved_eur"] * zone_share,
}

if zone_kpi["risk_eur"] > 50000:
    risk_flag = "YÜKSEK"
elif zone_kpi["risk_eur"] > 20000:
    risk_flag = "ORTA"
else:
    risk_flag = "DÜŞÜK"


def render_right_panel():
    st.subheader("Zon Özeti")
    st.write(f"**Zon:** {selected_zone.get('name','-')}")
    st.write(f"**Alan:** {selected_zone.get('area_m2','-')} m²")
    st.write(f"**Pay:** %{(zone_share*100):.1f}")
    st.write(f"**Risk Seviyesi:** {risk_flag}")

    st.divider()
    st.subheader("Zon KPI (BIOLOT)")
    a1, a2 = st.columns(2)
    a1.metric("Zon Toplam CO2 (t/yıl)", f"{zone_kpi['total_ton']:.2f}")
    a2.metric("Zon Karbon Riski (€)", f"{zone_kpi['risk_eur']:.0f}")

    b1, b2 = st.columns(2)
    b1.metric("Zon HVAC Tasarruf (kWh/yıl)", f"{zone_kpi['hvac_saved_kwh']:.0f}")
    b2.metric("Zon HVAC (€)", f"{zone_kpi['hvac_saved_eur']:.0f}")

    c1, c2 = st.columns(2)
    c1.metric("Zon Su Tasarruf (m³/yıl)", f"{zone_kpi['water_saved_m3']:.0f}")
    c2.metric("Zon Pompa kWh", f"{zone_kpi['pump_saved_kwh']:.0f}")

    d1, d2 = st.columns(2)
    d1.metric("Zon Toplam kWh", f"{zone_kpi['total_saved_kwh']:.0f}")
    d2.metric("Zon Toplam (€)", f"{zone_kpi['total_saved_eur']:.0f}")

    st.divider()
    with st.expander("Denetlenebilir çıktı (motor JSON)"):
        st.json(out)


def render_map_mode():
    center_lat, center_lon = centroid_latlon(selected_zone["polygon"])
    m = folium.Map(location=[center_lat, center_lon], zoom_start=17, control_scale=True)

    if show_zones:
        zones_fg = folium.FeatureGroup(name="Zonlar", show=True)
        for z in zones:
            poly = z["polygon"]
            style = z.get("style", {})
            color = style.get("color", "#2E7D32")
            fill_color = style.get("fillColor", "#66BB6A")
            fill_opacity = style.get("fillOpacity", 0.25)
            folium.Polygon(
                locations=poly,
                color=color,
                fill=True,
                fill_color=fill_color,
                fill_opacity=fill_opacity,
                weight=3,
                tooltip=z.get("name", "Zon"),
            ).add_to(zones_fg)
        zones_fg.add_to(m)

    if show_sensors:
        sens_fg = folium.FeatureGroup(name="Sensörler", show=True)
        for s in sensors:
            folium.CircleMarker(
                location=[s["lat"], s["lon"]],
                radius=6,
                color="#1565C0",
                fill=True,
                fill_color="#1E88E5",
                fill_opacity=0.9,
                tooltip=s.get("name", "Sensör"),
            ).add_to(sens_fg)
        sens_fg.add_to(m)

    if show_heatmap:
        heat_points = []
        for s in sensors:
            temp = s.get("last", {}).get("temp_c", None)
            if temp is not None:
                heat_points.append([s["lat"], s["lon"], float(temp)])
        if heat_points:
            hm_fg = folium.FeatureGroup(name="Isı Haritası (Temp)", show=True)
            HeatMap(heat_points, radius=28, blur=20, min_opacity=0.25).add_to(hm_fg)
            hm_fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, height=620, width=None)


def render_plan_mode():
    img_path = load_plan_image_path()
    if not img_path:
        st.warning("assets/site_plan.png (veya .jpg) bulunamadı. Lütfen görseli 'assets' klasörüne yükle.")
        st.stop()

    img = Image.open(img_path)
    width, height = img.size
    img_uri = image_to_data_uri(img_path)

    fig = go.Figure()

    # ✅ En kritik düzeltme:
    # Plotly'de piksel koordinatı mantığı için görseli "top-left" oturtuyoruz:
    # x=0 (sol), y=height (üst), y ekseni ters çevrildiğinde birebir oturur.
    fig.add_layout_image(
        dict(
            source=img_uri,
            xref="x",
            yref="y",
            x=0,
            y=height,
            sizex=width,
            sizey=height,
            xanchor="left",
            yanchor="top",
            sizing="stretch",
            layer="below",
            opacity=1.0,
        )
    )

    # Koordinat taşmalarını say (debug)
    clipped_polys = 0
    clipped_points = 0

    # ✅ Zonlar (clamp ile taşma yok)
    if show_zones:
        for z in zones:
            poly_px = z.get("polygon_px")
            if not poly_px:
                continue

            xs, ys = [], []
            before_clip = False

            for p in poly_px:
                x0 = float(p[0])
                y0 = float(p[1])
                x1, y1 = clamp_point_xy(x0, y0, width, height)
                if x0 != x1 or y0 != y1:
                    before_clip = True
                xs.append(x1)
                ys.append(y1)

            # kapat
            xs.append(xs[0])
            ys.append(ys[0])

            if before_clip:
                clipped_polys += 1

            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    name=z.get("name", "Zon"),
                    line=dict(width=3),
                )
            )

    # ✅ Sensörler (clamp ile taşma yok)
    if show_sensors:
        xs, ys, names = [], [], []
        for s in sensors:
            if "x" in s and "y" in s:
                x0 = float(s["x"])
                y0 = float(s["y"])
                x1, y1 = clamp_point_xy(x0, y0, width, height)
                if x0 != x1 or y0 != y1:
                    clipped_points += 1
                xs.append(x1)
                ys.append(y1)
                names.append(s.get("name", "Sensör"))

        if xs:
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="markers+text",
                    text=names,
                    textposition="top center",
                    marker=dict(size=12),
                    name="Sensörler",
                )
            )

    # ✅ Piksel ekseni ayarı:
    # x: 0..width, y: 0..height (0 üstte kalsın diye y range ters)
    fig.update_xaxes(visible=False, range=[0, width], fixedrange=True)
    fig.update_yaxes(visible=False, range=[height, 0], fixedrange=True, scaleanchor="x")

    fig.update_layout(
        height=650,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Debug uyarısı (sunumdan önce kontrol)
    if clipped_polys > 0 or clipped_points > 0:
        st.warning(
            f"Plan koordinatlarında taşma vardı ve otomatik düzeltildi. "
            f"Zon (clamp): {clipped_polys} | Sensör (clamp): {clipped_points}. "
            f"(Sunum için sorun değil; veri kalibrasyonu sonrası sıfırlanır.)"
        )


# ---------------- Layout ----------------
left, right = st.columns([2, 1], gap="large")

with left:
    st.subheader("Harita / Plan")
    if view_mode == "Harita Modu":
        render_map_mode()
    else:
        render_plan_mode()

with right:
    render_right_panel()
