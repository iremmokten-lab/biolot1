import streamlit as st
import json
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# -------------------------------
# MOTOR IMPORT
# -------------------------------
try:
    from engine import run_biolot, BIOL0T_ENGINE_VERSION
except Exception as e:
    st.error("Hesap motoru yüklenemedi (engine import hatası).")
    st.code(str(e))
    st.stop()

# -------------------------------
# AUDIT LOG HELPERS
# -------------------------------
AUDIT_LOG_DIR = "audit_logs"
AUDIT_LOG_FILE = os.path.join(AUDIT_LOG_DIR, "runs.jsonl")

def append_audit_log(run_id: str, engine_version: str, facility_id: str, inputs: dict, outputs: dict) -> None:
    os.makedirs(AUDIT_LOG_DIR, exist_ok=True)
    record = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": engine_version,
        "facility_id": facility_id,
        "inputs": inputs,
        "summary": {
            "scope1_ton": outputs.get("carbon", {}).get("scope1_ton"),
            "scope2_ton": outputs.get("carbon", {}).get("scope2_ton"),
            "total_ton": outputs.get("carbon", {}).get("total_ton"),
            "total_saved_kwh": outputs.get("total_operational_gain", {}).get("total_saved_kwh"),
            "total_saved_co2_ton": outputs.get("total_operational_gain", {}).get("total_saved_co2_ton"),
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
# SESSION STATE INIT
# -------------------------------
if "facilities" not in st.session_state:
    st.session_state["facilities"] = [{"facility_id": "FAC-001", "inputs": dict(DEFAULT_INPUTS)}]
if "portfolio_result" not in st.session_state:
    st.session_state["portfolio_result"] = None

# -------------------------------
# PDF HELPERS
# -------------------------------
def _bar_png(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> bytes:
    buf = BytesIO()
    plt.figure()
    plt.bar(df[x_col].astype(str), df[y_col].astype(float))
    plt.title(title)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    return buf.getvalue()

def build_portfolio_pdf_bytes(portfolio: dict, df_table: pd.DataFrame | None) -> bytes:
    styles = getSampleStyleSheet()
    story = []

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    engine_v = str(portfolio.get("meta", {}).get("engine_version", BIOL0T_ENGINE_VERSION))
    facility_count = int(portfolio.get("meta", {}).get("facility_count", 0))

    story.append(Paragraph("BIOLOT – Portfolio Performance Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated: {now_utc}", styles["Normal"]))
    story.append(Paragraph(f"Engine Version: {engine_v}", styles["Normal"]))
    story.append(Paragraph(f"Facilities: {facility_count}", styles["Normal"]))
    story.append(Spacer(1, 16))

    totals = portfolio.get("portfolio_totals", {})
    kpi_data = [
        ["KPI", "Value"],
        ["Total Emissions (tCO2e/y)", f"{float(totals.get('total_ton', 0.0)):.2f}"],
        ["Scope 1 (t/y)", f"{float(totals.get('scope1_ton', 0.0)):.2f}"],
        ["Scope 2 (t/y)", f"{float(totals.get('scope2_ton', 0.0)):.2f}"],
        ["Total Energy Saved (kWh/y)", f"{float(totals.get('total_saved_kwh', 0.0)):.0f}"],
        ["Total Avoided Cost (€/y)", f"{float(totals.get('total_saved_eur', 0.0)):.2f}"],
        ["Total Avoided CO2 (t/y)", f"{float(totals.get('total_saved_co2_ton', 0.0)):.3f}"],
    ]

    story.append(Paragraph("Portfolio KPI Summary", styles["Heading2"]))
    t = Table(kpi_data, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Facility Comparison (Top Rows)", styles["Heading2"]))
    if df_table is not None and len(df_table) > 0:
        df_pdf = df_table.head(12).copy()
        cols = ["facility_id", "total_ton", "saved_eur", "saved_kwh"]
        df_pdf = df_pdf[cols]
        table_data = [cols] + df_pdf.values.tolist()
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("PADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No facility data available.", styles["Normal"]))

    story.append(Spacer(1, 14))
    story.append(Paragraph("Charts", styles["Heading2"]))

    if df_table is not None and len(df_table) > 0:
        df_chart = df_table.head(8).copy()
        img1 = Image(BytesIO(_bar_png(df_chart, "facility_id", "total_ton", "Total Emissions by Facility (Top 8)")), width=500, height=260)
        story.append(img1)
        story.append(Spacer(1, 10))
        img2 = Image(BytesIO(_bar_png(df_chart, "facility_id", "saved_eur", "Avoided Cost (€) by Facility (Top 8)")), width=500, height=260)
        story.append(img2)
    else:
        story.append(Paragraph("Charts skipped (no data).", styles["Normal"]))

    pdf_buf = BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=A4, title="BIOLOT Portfolio Report")
    doc.build(story)
    return pdf_buf.getvalue()

# -------------------------------
# UI
# -------------------------------
st.set_page_config(page_title="BIOLOT", layout="wide")
st.title("BIOLOT – Portfolio Dashboard + PDF Export")
st.caption(f"Motor Versiyonu: {BIOL0T_ENGINE_VERSION}")

st.divider()
st.subheader("Tesis Yönetimi")

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    new_facility_id = st.text_input("Yeni Tesis ID", value=f"FAC-{len(st.session_state['facilities'])+1:03d}")
with c2:
    if st.button("➕ Tesis Ekle", use_container_width=True):
        existing = [f["facility_id"] for f in st.session_state["facilities"]]
        if new_facility_id.strip() == "":
            st.warning("Tesis ID boş olamaz.")
        elif new_facility_id in existing:
            st.warning("Bu Tesis ID zaten var. Farklı bir ID yaz.")
        else:
            st.session_state["facilities"].append({"facility_id": new_facility_id, "inputs": dict(DEFAULT_INPUTS)})
            st.session_state["portfolio_result"] = None
            st.success(f"{new_facility_id} eklendi.")
with c3:
    if st.button("🧹 Portfolio Sonucunu Temizle", use_container_width=True):
        st.session_state["portfolio_result"] = None
        st.success("Portfolio sonucu temizlendi.")

remove_options = ["(silme)"] + [f["facility_id"] for f in st.session_state["facilities"]]
remove_id = st.selectbox("Silmek istediğin tesisi seç (opsiyonel)", options=remove_options)
if st.button("🗑️ Seçili Tesisi Sil", disabled=(remove_id == "(silme)")):
    st.session_state["facilities"] = [f for f in st.session_state["facilities"] if f["facility_id"] != remove_id]
    st.session_state["portfolio_result"] = None
    st.success(f"{remove_id} silindi.")

st.divider()
st.subheader("Tesis Girdileri")

for idx, fac in enumerate(st.session_state["facilities"]):
    fid = fac["facility_id"]
    inputs = fac["inputs"]

    with st.expander(f"🏭 {fid} – Girdileri Düzenle", expanded=(idx == 0)):
        colA, colB, colC = st.columns(3)
        with colA:
            electricity_kwh_year = st.number_input("Yıllık Elektrik (kWh)", min_value=0.0, value=float(inputs["electricity_kwh_year"]), key=f"{fid}_electricity")
            natural_gas_m3_year = st.number_input("Yıllık Doğalgaz (m3)", min_value=0.0, value=float(inputs["natural_gas_m3_year"]), key=f"{fid}_gas")
            area_m2 = st.number_input("Toplam Alan (m2)", min_value=1.0, value=float(inputs["area_m2"]), key=f"{fid}_area")
        with colB:
            carbon_price = st.number_input("Karbon Fiyatı (€/ton)", min_value=0.0, value=float(inputs["carbon_price"]), key=f"{fid}_carbon_price")
            grid_factor = st.number_input("Elektrik Emisyon Faktörü (kgCO2/kWh)", min_value=0.0, value=float(inputs["grid_factor"]), key=f"{fid}_grid_factor")
            gas_factor = st.number_input("Gaz Emisyon Faktörü (kgCO2/m3)", min_value=0.0, value=float(inputs["gas_factor"]), key=f"{fid}_gas_factor")
        with colC:
            delta_t = st.number_input("Yeşil Soğutma Etkisi (°C)", min_value=0.0, value=float(inputs["delta_t"]), key=f"{fid}_delta_t")
            energy_sensitivity = st.number_input("1°C Başına Enerji Azalış Oranı", min_value=0.0, value=float(inputs["energy_sensitivity"]), key=f"{fid}_energy_sens")
            beta = st.number_input("Bina Elastikiyet Katsayısı", min_value=0.0, value=float(inputs["beta"]), key=f"{fid}_beta")

        st.markdown("**Su / Pompa**")
        w1, w2, w3 = st.columns(3)
        with w1:
            water_baseline = st.number_input("Referans Su (m3/yıl)", min_value=0.0, value=float(inputs["water_baseline"]), key=f"{fid}_water_base")
        with w2:
            water_actual = st.number_input("Mevcut Su (m3/yıl)", min_value=0.0, value=float(inputs["water_actual"]), key=f"{fid}_water_act")
        with w3:
            pump_kwh_per_m3 = st.number_input("Pompa Enerji İndeksi (kWh/m3)", min_value=0.0, value=float(inputs["pump_kwh_per_m3"]), key=f"{fid}_pump_idx")

        fac["inputs"] = {
            "electricity_kwh_year": electricity_kwh_year,
            "natural_gas_m3_year": natural_gas_m3_year,
            "area_m2": area_m2,
            "carbon_price": carbon_price,
            "grid_factor": grid_factor,
            "gas_factor": gas_factor,
            "delta_t": delta_t,
            "energy_sensitivity": energy_sensitivity,
            "beta": beta,
            "water_baseline": water_baseline,
            "water_actual": water_actual,
            "pump_kwh_per_m3": pump_kwh_per_m3,
        }

st.divider()
st.subheader("Portfolio Analizi")
run_all = st.button("🚀 Tüm Tesisleri Çalıştır", type="primary", use_container_width=True)

if run_all:
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
        append_audit_log(run_id, str(BIOL0T_ENGINE_VERSION), facility_id=fid, inputs=inp, outputs=out)

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
    st.success("Portfolio analizi tamamlandı.")

portfolio = st.session_state.get("portfolio_result")
if portfolio:
    totals = portfolio["portfolio_totals"]

    st.subheader("Portfolio KPI'lar")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Tesis", f"{portfolio['meta']['facility_count']}")
    k2.metric("Toplam Emisyon (tCO2e/yıl)", f"{totals['total_ton']:.2f}")
    k3.metric("Scope 1 (t/yıl)", f"{totals['scope1_ton']:.2f}")
    k4.metric("Scope 2 (t/yıl)", f"{totals['scope2_ton']:.2f}")
    k5.metric("Toplam Tasarruf (kWh/yıl)", f"{totals['total_saved_kwh']:.0f}")
    k6.metric("Toplam Kaçınılan Maliyet (€ / yıl)", f"{totals['total_saved_eur']:.2f}")

    rows = []
    for f in portfolio["facilities"]:
        fid = f["facility_id"]
        out = f["outputs"]
        carbon = out.get("carbon", {})
        gain = out.get("total_operational_gain", {})
        rows.append({
            "facility_id": fid,
            "scope1_ton": float(carbon.get("scope1_ton", 0.0)),
            "scope2_ton": float(carbon.get("scope2_ton", 0.0)),
            "total_ton": float(carbon.get("total_ton", 0.0)),
            "saved_kwh": float(gain.get("total_saved_kwh", 0.0)),
            "saved_co2_ton": float(gain.get("total_saved_co2_ton", 0.0)),
            "saved_eur": float(gain.get("total_saved_eur", 0.0)),
        })

    df = pd.DataFrame(rows).sort_values("total_ton", ascending=False)
    st.divider()
    st.subheader("Tesis Tablosu")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Grafikler")
    max_n = len(df)
    top_n = st.slider("Grafikte gösterilecek tesis sayısı (Top N)", 1, max_n, min(5, max_n))
    df_top = df.head(top_n).set_index("facility_id")
    st.bar_chart(df_top[["scope1_ton", "scope2_ton", "total_ton"]], use_container_width=True)
    st.bar_chart(df_top[["saved_eur"]], use_container_width=True)
    st.bar_chart(df_top[["saved_kwh"]], use_container_width=True)

    st.divider()
    st.subheader("PDF Export (Yatırımcı Raporu)")
    try:
        pdf_bytes = build_portfolio_pdf_bytes(portfolio, df)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        st.download_button(
            "⬇️ PDF Raporunu indir",
            data=pdf_bytes,
            file_name=f"biolot_report_v{BIOL0T_ENGINE_VERSION}_{ts}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.error("PDF üretiminde hata oldu. requirements.txt doğru mu kontrol et.")
        st.code(str(e))

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
    st.info("Portfolio için 'Tüm Tesisleri Çalıştır' bas.")
