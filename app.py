import streamlit as st
import json
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
import plotly.express as px

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# -------------------------------
# ENGINE IMPORT
# -------------------------------
try:
    from engine import run_biolot, BIOL0T_ENGINE_VERSION
except Exception as e:
    st.error("Hesap motoru (engine) yüklenemedi.")
    st.code(str(e))
    st.stop()

# -------------------------------
# DEFAULT INPUTS
# -------------------------------
DEFAULT_INPUTS = {
    "electricity_kwh_year": 2500000.0,
    "natural_gas_m3_year": 180000.0,
    "area_m2": 20000.0,
    "carbon_price": 85.5,
    "grid_factor": 0.43,
    "gas_factor": 2.0,
    "delta_t": 2.4,
    "energy_sensitivity": 0.04,
    "beta": 0.5,
    "water_baseline": 12000.0,
    "water_actual": 8000.0,
    "pump_kwh_per_m3": 0.4,
}

# -------------------------------
# AUDIT LOG (Append-only)
# -------------------------------
AUDIT_LOG_DIR = "audit_logs"
AUDIT_LOG_FILE = os.path.join(AUDIT_LOG_DIR, "runs.jsonl")

def append_audit_log(run_id: str, facility_id: str, inputs: dict, outputs: dict) -> None:
    os.makedirs(AUDIT_LOG_DIR, exist_ok=True)
    record = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": str(BIOL0T_ENGINE_VERSION),
        "facility_id": facility_id,
        "inputs": inputs,
        "summary": {
            "scope1_ton": outputs.get("carbon", {}).get("scope1_ton"),
            "scope2_ton": outputs.get("carbon", {}).get("scope2_ton"),
            "total_ton": outputs.get("carbon", {}).get("total_ton"),
            "total_saved_eur": outputs.get("total_operational_gain", {}).get("total_saved_eur"),
        },
    }
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_audit_log_text() -> str:
    if not os.path.exists(AUDIT_LOG_FILE):
        return ""
    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        return f.read()

# -------------------------------
# FONT SETUP (Türkçe karakterler için)
# -------------------------------
def setup_fonts():
    """
    Repo içinde şu dosyalar olmalı:
      fonts/DejaVuSans.ttf
      fonts/DejaVuSans-Bold.ttf
    """
    base_font = "Helvetica"
    bold_font = "Helvetica-Bold"

    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", "fonts/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", "fonts/DejaVuSans-Bold.ttf"))
        base_font = "DejaVuSans"
        bold_font = "DejaVuSans-Bold"
    except Exception:
        # Font bulunamazsa PDF Türkçe karakterleri bozabilir
        pass

    return base_font, bold_font

# -------------------------------
# PDF BUILDER
# -------------------------------
def build_portfolio_pdf_bytes(portfolio: dict, df: pd.DataFrame) -> bytes:
    base_font, bold_font = setup_fonts()

    styles = getSampleStyleSheet()
    story = []

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story.append(Paragraph(f"<font name='{bold_font}'>BIOLOT – Portföy Raporu</font>", styles["Title"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<font name='{base_font}'>Oluşturulma: {now_utc}</font>", styles["Normal"]))
    story.append(Paragraph(f"<font name='{base_font}'>Motor Versiyonu: {BIOL0T_ENGINE_VERSION}</font>", styles["Normal"]))
    story.append(Spacer(1, 14))

    totals = portfolio["portfolio_totals"]
    kpi_data = [
        ["Gösterge", "Değer"],
        ["Toplam Emisyon (tCO2e/yıl)", f"{totals['total_ton']:.2f}"],
        ["Scope 1 (t/yıl)", f"{totals['scope1_ton']:.2f}"],
        ["Scope 2 (t/yıl)", f"{totals['scope2_ton']:.2f}"],
        ["Toplam Enerji Tasarrufu (kWh/yıl)", f"{totals['total_saved_kwh']:.0f}"],
        ["Toplam Kaçınılan Maliyet (€ / yıl)", f"{totals['total_saved_eur']:.2f}"],
        ["Toplam Önlenen CO2 (t/yıl)", f"{totals['total_saved_co2_ton']:.3f}"],
    ]

    t = Table(kpi_data, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,0), bold_font),
        ("FONTNAME", (0,1), (-1,-1), base_font),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    story.append(Paragraph(f"<font name='{bold_font}'>Tesis Özeti (Tablo)</font>", styles["Heading2"]))
    if len(df) > 0:
        df_pdf = df.head(15).copy()
        table_data = [df_pdf.columns.tolist()] + df_pdf.values.tolist()
        t2 = Table(table_data, hAlign="LEFT")
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTNAME", (0,0), (-1,0), bold_font),
            ("FONTNAME", (0,1), (-1,-1), base_font),
            ("PADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(t2)
    else:
        story.append(Paragraph(f"<font name='{base_font}'>Tablo için veri yok.</font>", styles["Normal"]))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="BIOLOT Portföy Raporu")
    doc.build(story)
    return buf.getvalue()

# -------------------------------
# SESSION STATE
# -------------------------------
if "facilities" not in st.session_state:
    st.session_state["facilities"] = [{"facility_id": "FAC-001", "inputs": dict(DEFAULT_INPUTS)}]
if "portfolio_result" not in st.session_state:
    st.session_state["portfolio_result"] = None

# -------------------------------
# UI
# -------------------------------
st.set_page_config(page_title="BIOLOT", layout="wide")
st.title("BIOLOT – Portföy Dashboard")
st.caption(f"Motor Versiyonu: {BIOL0T_ENGINE_VERSION}")

st.divider()

st.subheader("Tesis Yönetimi")

col1, col2 = st.columns([2, 1])
with col1:
    new_facility_id = st.text_input("Yeni Tesis ID", value=f"FAC-{len(st.session_state['facilities'])+1:03d}")
with col2:
    if st.button("➕ Tesis Ekle", use_container_width=True):
        ids = [f["facility_id"] for f in st.session_state["facilities"]]
        if new_facility_id.strip() == "":
            st.warning("Tesis ID boş olamaz.")
        elif new_facility_id in ids:
            st.warning("Bu tesis ID zaten var. Farklı bir ID yaz.")
        else:
            st.session_state["facilities"].append({"facility_id": new_facility_id, "inputs": dict(DEFAULT_INPUTS)})
            st.session_state["portfolio_result"] = None
            st.success(f"{new_facility_id} eklendi.")

remove_options = ["(silme)"] + [f["facility_id"] for f in st.session_state["facilities"]]
remove_id = st.selectbox("Silmek istediğin tesisi seç", remove_options)
if st.button("🗑️ Seçili Tesisi Sil", disabled=(remove_id == "(silme)")):
    st.session_state["facilities"] = [f for f in st.session_state["facilities"] if f["facility_id"] != remove_id]
    st.session_state["portfolio_result"] = None
    st.success(f"{remove_id} silindi.")

st.divider()

st.subheader("Tesis Girdileri")

if len(st.session_state["facilities"]) == 0:
    st.warning("Hiç tesis yok. Üstten 'Tesis Ekle' ile en az 1 tesis ekle.")
else:
    for idx, fac in enumerate(st.session_state["facilities"]):
        fid = fac["facility_id"]
        inp = fac["inputs"]

        with st.expander(f"🏭 {fid} – Girdileri Düzenle", expanded=(idx == 0)):
            a, b, c = st.columns(3)

            with a:
                inp["electricity_kwh_year"] = st.number_input("Yıllık Elektrik (kWh)", min_value=0.0, value=float(inp["electricity_kwh_year"]), key=f"{fid}_el")
                inp["natural_gas_m3_year"] = st.number_input("Yıllık Doğalgaz (m³)", min_value=0.0, value=float(inp["natural_gas_m3_year"]), key=f"{fid}_gas")
                inp["area_m2"] = st.number_input("Toplam Alan (m²)", min_value=1.0, value=float(inp["area_m2"]), key=f"{fid}_area")

            with b:
                inp["carbon_price"] = st.number_input("Karbon Fiyatı (€/ton)", min_value=0.0, value=float(inp["carbon_price"]), key=f"{fid}_cp")
                inp["grid_factor"] = st.number_input("Elektrik Emisyon Faktörü (kgCO2/kWh)", min_value=0.0, value=float(inp["grid_factor"]), key=f"{fid}_gf")
                inp["gas_factor"] = st.number_input("Gaz Emisyon Faktörü (kgCO2/m³)", min_value=0.0, value=float(inp["gas_factor"]), key=f"{fid}_gaf")

            with c:
                inp["delta_t"] = st.number_input("Mikroklima Etkisi (°C)", min_value=0.0, value=float(inp["delta_t"]), key=f"{fid}_dt")
                inp["energy_sensitivity"] = st.number_input("1°C Başına Enerji Azalış Oranı", min_value=0.0, value=float(inp["energy_sensitivity"]), key=f"{fid}_es")
                inp["beta"] = st.number_input("Bina Elastikiyet Katsayısı", min_value=0.0, value=float(inp["beta"]), key=f"{fid}_beta")

            st.markdown("**Su / Pompa**")
            w1, w2, w3 = st.columns(3)
            with w1:
                inp["water_baseline"] = st.number_input("Referans Su (m³/yıl)", min_value=0.0, value=float(inp["water_baseline"]), key=f"{fid}_wb")
            with w2:
                inp["water_actual"] = st.number_input("Mevcut Su (m³/yıl)", min_value=0.0, value=float(inp["water_actual"]), key=f"{fid}_wa")
            with w3:
                inp["pump_kwh_per_m3"] = st.number_input("Pompa Enerji İndeksi (kWh/m³)", min_value=0.0, value=float(inp["pump_kwh_per_m3"]), key=f"{fid}_pk")

            fac["inputs"] = inp

st.divider()

st.subheader("Portföy Analizi")

run_all = st.button("🚀 Tüm Tesisleri Çalıştır", type="primary")

if run_all:
    if len(st.session_state["facilities"]) == 0:
        st.error("Çalıştırmak için en az 1 tesis eklemelisin.")
        st.stop()

    portfolio = {
        "meta": {
            "portfolio_id": "BIOLOT-PORTFOLIO",
            "engine_version": str(BIOL0T_ENGINE_VERSION),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "facility_count": len(st.session_state["facilities"]),
        },
        "facilities": [],
        "portfolio_totals": {
            "scope1_ton": 0.0,
            "scope2_ton": 0.0,
            "total_ton": 0.0,
            "total_saved_kwh": 0.0,
            "total_saved_co2_ton": 0.0,
            "total_saved_eur": 0.0,
        },
    }

    for fac in st.session_state["facilities"]:
        fid = fac["facility_id"]
        inp = fac["inputs"]

        out = run_biolot(**inp)

        run_id = str(uuid.uuid4())
        append_audit_log(run_id, facility_id=fid, inputs=inp, outputs=out)

        portfolio["facilities"].append({"facility_id": fid, "run_id": run_id, "inputs": inp, "outputs": out})

        c = out.get("carbon", {})
        t = out.get("total_operational_gain", {})

        portfolio["portfolio_totals"]["scope1_ton"] += float(c.get("scope1_ton", 0.0))
        portfolio["portfolio_totals"]["scope2_ton"] += float(c.get("scope2_ton", 0.0))
        portfolio["portfolio_totals"]["total_ton"] += float(c.get("total_ton", 0.0))
        portfolio["portfolio_totals"]["total_saved_kwh"] += float(t.get("total_saved_kwh", 0.0))
        portfolio["portfolio_totals"]["total_saved_co2_ton"] += float(t.get("total_saved_co2_ton", 0.0))
        portfolio["portfolio_totals"]["total_saved_eur"] += float(t.get("total_saved_eur", 0.0))

    st.session_state["portfolio_result"] = portfolio
    st.success("Portföy analizi tamamlandı.")

portfolio = st.session_state.get("portfolio_result")

if portfolio:
    totals = portfolio["portfolio_totals"]

    st.subheader("Portföy KPI")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Emisyon (tCO2e/yıl)", f"{totals['total_ton']:.2f}")
    k2.metric("Scope 1 (t/yıl)", f"{totals['scope1_ton']:.2f}")
    k3.metric("Scope 2 (t/yıl)", f"{totals['scope2_ton']:.2f}")
    k4.metric("Toplam Kaçınılan Maliyet (€ / yıl)", f"{totals['total_saved_eur']:.2f}")
st.divider()
st.subheader("✅ Karbon Vergisi / ETS Hazırlık (Senaryo)")

colA, colB, colC = st.columns([1, 1, 2])

with colA:
    ets_price = st.number_input(
        "Karbon Fiyatı (€/tCO2)",
        min_value=0.0,
        value=50.0,
        step=5.0,
        help="Senaryo amaçlı fiyat. Resmi ETS/karbon vergisi metodolojisi yürürlüğe girdiğinde güncellenecektir."
    )

with colB:
    ets_mode = st.selectbox(
        "Senaryo",
        ["Conservative", "Base", "Aggressive"],
        index=1,
        help="2026–2028 fiyat projeksiyonu demo amaçlıdır."
    )

# 2026–2028 senaryo fiyatları (demo amaçlı)
if ets_mode == "Conservative":
    years = [2026, 2027, 2028]
    prices = [25, 30, 35]
elif ets_mode == "Aggressive":
    years = [2026, 2027, 2028]
    prices = [60, 75, 90]
else:  # Base
    years = [2026, 2027, 2028]
    prices = [40, 50, 60]

df_ets = pd.DataFrame({"Yıl": years, "Fiyat (€/tCO2)": prices})

with colC:
    fig = px.line(df_ets, x="Yıl", y="Fiyat (€/tCO2)", markers=True)
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# Tahmini yükümlülük (senaryo)
total_tco2 = float(totals["total_ton"])
ets_liability_eur = total_tco2 * float(ets_price)

m1, m2, m3 = st.columns(3)
m1.metric("Toplam Emisyon (tCO2e/yıl)", f"{total_tco2:,.2f}")
m2.metric("Seçili Fiyat (€/tCO2)", f"{float(ets_price):,.2f}")
m3.metric("Tahmini Yükümlülük (€)", f"{ets_liability_eur:,.0f}")

st.caption(
    "Bu bölüm **senaryo amaçlıdır**. Resmi ETS/karbon vergisi metodolojisi yürürlüğe girdiğinde "
    "hesaplama parametreleri ve raporlama formatı **resmi metodolojiye göre güncellenecektir**."
)

    rows = []
    for f in portfolio["facilities"]:
        fid = f["facility_id"]
        out = f["outputs"]
        carbon = out.get("carbon", {})
        gain = out.get("total_operational_gain", {})
        rows.append({
            "tesis_id": fid,
            "toplam_emisyon_ton": float(carbon.get("total_ton", 0.0)),
            "scope1_ton": float(carbon.get("scope1_ton", 0.0)),
            "scope2_ton": float(carbon.get("scope2_ton", 0.0)),
            "tasarruf_eur": float(gain.get("total_saved_eur", 0.0)),
            "tasarruf_kwh": float(gain.get("total_saved_kwh", 0.0)),
        })

    df = pd.DataFrame(rows).sort_values("toplam_emisyon_ton", ascending=False)

    st.divider()
    st.subheader("Tesis Tablosu")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Grafikler")

    df_chart = df.set_index("tesis_id")
    st.bar_chart(df_chart[["scope1_ton", "scope2_ton", "toplam_emisyon_ton"]], use_container_width=True)
    st.bar_chart(df_chart[["tasarruf_eur"]], use_container_width=True)
    st.bar_chart(df_chart[["tasarruf_kwh"]], use_container_width=True)

    st.divider()
    st.subheader("PDF Export (Yatırımcı Raporu)")

    pdf_bytes = build_portfolio_pdf_bytes(portfolio, df)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    st.download_button(
        "⬇️ PDF Raporunu İndir",
        data=pdf_bytes,
        file_name=f"biolot_portfoy_raporu_v{BIOL0T_ENGINE_VERSION}_{ts}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    st.divider()
    st.subheader("Denetlenebilir Çıktılar")

    with st.expander("Portföy JSON (indirilebilir)"):
        json_text = json.dumps(portfolio, ensure_ascii=False, indent=2, sort_keys=True)
        st.download_button(
            "⬇️ Portföy JSON'u indir",
            data=json_text.encode("utf-8"),
            file_name=f"biolot_portfoy_v{BIOL0T_ENGINE_VERSION}_{ts}.json",
            mime="application/json",
            use_container_width=True,
        )
        st.json(portfolio)

    st.divider()
    st.subheader("Audit Log")

    log_text = read_audit_log_text()
    if log_text:
        st.download_button(
            "⬇️ Audit log dosyasını indir (runs.jsonl)",
            data=log_text.encode("utf-8"),
            file_name="runs.jsonl",
            mime="application/jsonl",
            use_container_width=True,
        )
    else:
        st.info("Henüz audit log yok. Portföy çalıştırınca oluşur.")
else:
    st.info("Üstten tesis ekleyip girdileri düzenledikten sonra 'Tüm Tesisleri Çalıştır' butonuna bas.")
