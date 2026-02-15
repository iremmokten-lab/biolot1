import streamlit as st
import json
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# -------------------------------
# MOTOR IMPORT
# -------------------------------
try:
    from engine import run_biolot, BIOL0T_ENGINE_VERSION
except Exception as e:
    st.error("Engine import hatası")
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

if "facilities" not in st.session_state:
    st.session_state["facilities"] = [{"facility_id": "FAC-001", "inputs": dict(DEFAULT_INPUTS)}]
if "portfolio_result" not in st.session_state:
    st.session_state["portfolio_result"] = None

# -------------------------------
# PDF BUILDER (Grafiksiz Stabil)
# -------------------------------
def build_portfolio_pdf_bytes(portfolio: dict, df: pd.DataFrame) -> bytes:
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("BIOLOT – Portfolio Performance Report", styles["Title"]))
    story.append(Spacer(1, 12))

    totals = portfolio["portfolio_totals"]

    kpi_data = [
        ["Metric", "Value"],
        ["Total Emissions (tCO2e/y)", f"{totals['total_ton']:.2f}"],
        ["Scope 1 (t/y)", f"{totals['scope1_ton']:.2f}"],
        ["Scope 2 (t/y)", f"{totals['scope2_ton']:.2f}"],
        ["Total Energy Saved (kWh/y)", f"{totals['total_saved_kwh']:.0f}"],
        ["Total Avoided Cost (€ / y)", f"{totals['total_saved_eur']:.2f}"],
    ]

    table = Table(kpi_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))

    # Facility Table
    if len(df) > 0:
        story.append(Paragraph("Facility Summary", styles["Heading2"]))
        table_data = [df.columns.tolist()] + df.values.tolist()
        table2 = Table(table_data)
        table2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(table2)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.build(story)

    return buffer.getvalue()

# -------------------------------
# UI
# -------------------------------
st.set_page_config(page_title="BIOLOT", layout="wide")
st.title("BIOLOT – Portfolio Dashboard")

st.divider()

if st.button("🚀 Tüm Tesisleri Çalıştır"):

    portfolio = {
        "portfolio_totals": {
            "scope1_ton": 0.0,
            "scope2_ton": 0.0,
            "total_ton": 0.0,
            "total_saved_kwh": 0.0,
            "total_saved_co2_ton": 0.0,
            "total_saved_eur": 0.0,
        },
        "facilities": []
    }

    for fac in st.session_state["facilities"]:
        fid = fac["facility_id"]
        inp = fac["inputs"]
        out = run_biolot(**inp)

        portfolio["facilities"].append({
            "facility_id": fid,
            "outputs": out
        })

        c = out["carbon"]
        t = out["total_operational_gain"]

        portfolio["portfolio_totals"]["scope1_ton"] += c["scope1_ton"]
        portfolio["portfolio_totals"]["scope2_ton"] += c["scope2_ton"]
        portfolio["portfolio_totals"]["total_ton"] += c["total_ton"]
        portfolio["portfolio_totals"]["total_saved_kwh"] += t["total_saved_kwh"]
        portfolio["portfolio_totals"]["total_saved_co2_ton"] += t["total_saved_co2_ton"]
        portfolio["portfolio_totals"]["total_saved_eur"] += t["total_saved_eur"]

    st.session_state["portfolio_result"] = portfolio
    st.success("Portfolio analizi tamamlandı.")

portfolio = st.session_state.get("portfolio_result")

if portfolio:

    totals = portfolio["portfolio_totals"]

    st.subheader("Portfolio KPI")
    st.metric("Toplam Emisyon (tCO2e)", f"{totals['total_ton']:.2f}")
    st.metric("Toplam Kaçınılan Maliyet (€)", f"{totals['total_saved_eur']:.2f}")

    rows = []
    for f in portfolio["facilities"]:
        fid = f["facility_id"]
        c = f["outputs"]["carbon"]
        t = f["outputs"]["total_operational_gain"]
        rows.append({
            "facility_id": fid,
            "total_ton": c["total_ton"],
            "saved_eur": t["total_saved_eur"],
            "saved_kwh": t["total_saved_kwh"],
        })

    df = pd.DataFrame(rows)

    st.divider()
    st.subheader("Tesis Tablosu")
    st.dataframe(df, use_container_width=True)

    st.divider()
    st.subheader("Grafikler")

    if len(df) > 0:
        df2 = df.set_index("facility_id")
        st.bar_chart(df2[["total_ton"]])
        st.bar_chart(df2[["saved_eur"]])
        st.bar_chart(df2[["saved_kwh"]])

    st.divider()
    st.subheader("PDF Export")

    pdf_bytes = build_portfolio_pdf_bytes(portfolio, df)
    st.download_button(
        "⬇️ PDF Raporunu indir",
        data=pdf_bytes,
        file_name="biolot_portfolio_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
