import streamlit as st
import json
from datetime import datetime, timezone
import os
import uuid
AUDIT_LOG_DIR = "audit_logs"
AUDIT_LOG_FILE = os.path.join(AUDIT_LOG_DIR, "runs.jsonl")

def append_audit_log(run_id: str, engine_version: str, inputs: dict, outputs: dict) -> None:
    os.makedirs(AUDIT_LOG_DIR, exist_ok=True)

    record = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": engine_version,
        "inputs": inputs,
        "summary": {
            "scope1_ton": outputs.get("carbon", {}).get("scope1_ton"),
            "scope2_ton": outputs.get("carbon", {}).get("scope2_ton"),
            "total_ton": outputs.get("carbon", {}).get("total_ton"),
            "total_saved_eur": outputs.get("total_operational_gain", {}).get("total_saved_eur"),
        },
    }

    # JSON Lines format: her satır 1 JSON kayıt (append-only)
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_audit_log_text() -> str:
    if not os.path.exists(AUDIT_LOG_FILE):
        return ""
    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        return f.read()


st.set_page_config(page_title="BIOLOT", layout="wide")
st.title("BIOLOT - Endüstriyel Çevresel Performans Platformu")

# -------------------------------
# MOTOR IMPORT
# -------------------------------
try:
    from engine import run_biolot, BIOL0T_ENGINE_VERSION
except Exception as e:
    st.error("Hesap motoru yüklenemedi.")
    st.code(str(e))
    st.stop()

st.caption(f"Motor Versiyonu: {BIOL0T_ENGINE_VERSION}")

# -------------------------------
# SIDEBAR – GİRDİLER
# -------------------------------
st.sidebar.header("Tesis Parametreleri")
electricity_kwh_year = st.sidebar.number_input("Yıllık Elektrik (kWh)", min_value=0.0, value=2500000.0)
natural_gas_m3_year = st.sidebar.number_input("Yıllık Doğalgaz (m3)", min_value=0.0, value=180000.0)
area_m2 = st.sidebar.number_input("Toplam Alan (m2)", min_value=1.0, value=20000.0)

st.sidebar.divider()
st.sidebar.subheader("Karbon Parametreleri")
carbon_price = st.sidebar.number_input("Karbon Fiyatı (€/ton)", min_value=0.0, value=85.5)
grid_factor = st.sidebar.number_input("Elektrik Emisyon Faktörü (kgCO2/kWh)", min_value=0.0, value=0.43)
gas_factor = st.sidebar.number_input("Gaz Emisyon Faktörü (kgCO2/m3)", min_value=0.0, value=2.0)

st.sidebar.divider()
st.sidebar.subheader("Mikroklima / HVAC")
delta_t = st.sidebar.number_input("Yeşil Soğutma Etkisi (°C)", min_value=0.0, value=2.4)
energy_sensitivity = st.sidebar.number_input("1°C Başına Enerji Azalış Oranı", min_value=0.0, value=0.04)
beta = st.sidebar.number_input("Bina Elastikiyet Katsayısı", min_value=0.0, value=0.5)

st.sidebar.divider()
st.sidebar.subheader("Su / Pompa")
water_baseline = st.sidebar.number_input("Referans Su (m3/yıl)", min_value=0.0, value=12000.0)
water_actual = st.sidebar.number_input("Mevcut Su (m3/yıl)", min_value=0.0, value=8000.0)
pump_kwh_per_m3 = st.sidebar.number_input("Pompa Enerji İndeksi (kWh/m3)", min_value=0.0, value=0.4)

# -------------------------------
# HESAPLAMA
# -------------------------------
st.divider()
st.subheader("Analiz Sonuçları")

run = st.button("Analizi Başlat", type="primary")

if run:
    out = run_biolot(
        electricity_kwh_year=electricity_kwh_year,
        natural_gas_m3_year=natural_gas_m3_year,
        area_m2=area_m2,
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
    run_id = str(uuid.uuid4())

    append_audit_log(
        run_id,
        str(BIOL0T_ENGINE_VERSION),
        inputs={
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
        },
        outputs=out,
    )

    karbon = out["carbon"]
    hvac = out["hvac"]
    su = out["water"]
    toplam = out["total_operational_gain"]

    st.subheader("Karbon Göstergeleri")
    k1, k2, k3 = st.columns(3)
    k1.metric("Scope 1 (ton/yıl)", f"{karbon['scope1_ton']:.2f}")
    k2.metric("Scope 2 (ton/yıl)", f"{karbon['scope2_ton']:.2f}")
    k3.metric("Toplam Emisyon (ton/yıl)", f"{karbon['total_ton']:.2f}")

    k4, k5, k6 = st.columns(3)
    k4.metric("Karbon Riski (€ / yıl)", f"{karbon['risk_eur']:.0f}")

    # yoğunluklar
    if electricity_kwh_year > 0:
        yogunluk_enerji = karbon["total_ton"] / (electricity_kwh_year / 1_000_000.0)
    else:
        yogunluk_enerji = 0.0

    yogunluk_alan = karbon["total_ton"] / (area_m2 / 1000.0)
    k5.metric("Emisyon Yoğunluğu (ton/GWh)", f"{yogunluk_enerji:.2f}")
    k6.metric("Alan Yoğunluğu (ton/1000m2)", f"{yogunluk_alan:.2f}")

    st.divider()
    st.subheader("Mikroklima Etkisi (HVAC)")
    h1, h2, h3 = st.columns(3)
    h1.metric("Enerji Tasarrufu (kWh/yıl)", f"{hvac['saved_kwh']:.0f}")
    h2.metric("Önlenen CO2 (ton/yıl)", f"{hvac['saved_co2_ton']:.2f}")
    h3.metric("Kaçınılan Maliyet (€ / yıl)", f"{hvac['saved_eur']:.0f}")

    st.divider()
    st.subheader("Su ve Pompa Verimliliği")
    s1, s2, s3 = st.columns(3)
    s1.metric("Tasarruf Edilen Su (m3/yıl)", f"{su['saved_water_m3']:.0f}")
    s2.metric("Pompa Enerji Tasarrufu (kWh/yıl)", f"{su['saved_pump_kwh']:.0f}")
    s3.metric("Kaçınılan Maliyet (€ / yıl)", f"{su['saved_eur']:.0f}")

    st.divider()
    st.subheader("Toplam Operasyonel Kazanç")
    t1, t2, t3 = st.columns(3)
    t1.metric("Toplam Enerji Tasarrufu (kWh/yıl)", f"{toplam['total_saved_kwh']:.0f}")
    t2.metric("Toplam Önlenen CO2 (ton/yıl)", f"{toplam['total_saved_co2_ton']:.2f}")
    t3.metric("Toplam Kaçınılan Maliyet (€ / yıl)", f"{toplam['total_saved_eur']:.0f}")

    st.divider()

    # ✅ JSON Preview + Download
    with st.expander("Denetlenebilir Çıktı (JSON)"):
        st.json(out)

        json_text = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"biolot_audit_v{BIOL0T_ENGINE_VERSION}_{ts}.json"

        st.download_button(
            label="⬇️ JSON'u indir (audit-ready)",
            data=json_text.encode("utf-8"),
            file_name=filename,
            mime="application/json",
            use_container_width=True,
        )

else:
    st.info("Parametreleri girin ve analizi başlatın.")
    st.divider()
st.subheader("Audit Log")

log_text = read_audit_log_text()
if log_text:
    st.download_button(
        label="⬇️ Audit log dosyasını indir (runs.jsonl)",
        data=log_text.encode("utf-8"),
        file_name="runs.jsonl",
        mime="application/jsonl",
        use_container_width=True,
    )
    st.caption("runs.jsonl: Her satır bir run kaydıdır (append-only).")
else:
    st.info("Henüz audit log kaydı yok. Analizi başlatınca oluşacak.")

