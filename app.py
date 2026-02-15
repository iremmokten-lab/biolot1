import streamlit as st
import json
import os
import uuid
from datetime import datetime, timezone

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
# DEFAULT INPUTS (her tesis için başlangıç)
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
    st.session_state["facilities"] = [
        {"facility_id": "FAC-001", "inputs": dict(DEFAULT_INPUTS)}
    ]

if "portfolio_result" not in st.session_state:
    st.session_state["portfolio_result"] = None

# -------------------------------
# STREAMLIT UI
# -------------------------------
st.set_page_config(page_title="BIOLOT", layout="wide")
st.title("BIOLOT – Multi-Facility (Portfolio) Analiz")
st.caption(f"Motor Versiyonu: {BIOL0T_ENGINE_VERSION}")

st.divider()

# -------------------------------
# ADD FACILITY (çok basit)
# -------------------------------
st.subheader("Tesis Yönetimi")

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    new_facility_id = st.text_input("Yeni Tesis ID", value=f"FAC-{len(st.session_state['facilities'])+1:03d}")
with c2:
    if st.button("➕ Tesis Ekle", use_container_width=True):
        # aynı ID varsa ekleme
        existing = [f["facility_id"] for f in st.session_state["facilities"]]
        if new_facility_id.strip() == "":
            st.warning("Tesis ID boş olamaz.")
        elif new_facility_id in existing:
            st.warning("Bu Tesis ID zaten var. Farklı bir ID yaz.")
        else:
            st.session_state["facilities"].append(
                {"facility_id": new_facility_id, "inputs": dict(DEFAULT_INPUTS)}
            )
            st.success(f"{new_facility_id} eklendi.")

with c3:
    if st.button("🧹 Portfolio Sonucunu Temizle", use_container_width=True):
        st.session_state["portfolio_result"] = None
        st.success("Portfolio sonucu temizlendi.")

st.caption("Her tesis için aşağıdan değerleri düzenle, sonra 'Tüm Tesisleri Çalıştır' bas.")

st.divider()

# -------------------------------
# FACILITY INPUT EDITORS
# -------------------------------
st.subheader("Tesis Girdileri")

# remove facility UI
remove_id = st.selectbox(
    "Silmek istediğin tesisi seç (opsiyonel)",
    options=["(silme)"] + [f["facility_id"] for f in st.session_state["facilities"]],
)
if st.button("🗑️ Seçili Tesisi Sil", disabled=(remove_id == "(silme)")):
    st.session_state["facilities"] = [f for f in st.session_state["facilities"] if f["facility_id"] != remove_id]
    st.success(f"{remove_id} silindi.")
    st.session_state["portfolio_result"] = None

# facility editors
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

        # Save back to session_state
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

# -------------------------------
# RUN ALL FACILITIES
# -------------------------------
st.subheader("Portfolio Analizi")

run_all = st.button("🚀 Tüm Tesisleri Çalıştır", type="primary", use_container_width=True)

def validate_inputs(fid: str, inp: dict) -> list:
    errors = []
    if inp["area_m2"] <= 0:
        errors.append(f"{fid}: area_m2 0 veya negatif olamaz.")
    if inp["electricity_kwh_year"] < 0 or inp["natural_gas_m3_year"] < 0:
        errors.append(f"{fid}: enerji değerleri negatif olamaz.")
    # uyarı değil, hata da değil — sadece bilgi
    return errors

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

    all_errors = []
    for fac in st.session_state["facilities"]:
        fid = fac["facility_id"]
        inp = fac["inputs"]

        all_errors.extend(validate_inputs(fid, inp))

    if all_errors:
        st.error("Girdi hataları var. Düzelttikten sonra tekrar çalıştır.")
        for e in all_errors:
            st.write("• " + e)
        st.stop()

    # Run each facility
    for fac in st.session_state["facilities"]:
        fid = fac["facility_id"]
        inp = fac["inputs"]

        # Uyarılar
        if inp["water_actual"] > inp["water_baseline"]:
            st.warning(f"{fid}: Mevcut su tüketimi referansın üzerinde görünüyor (kontrol edin).")
        if inp["grid_factor"] > 1.5:
            st.warning(f"{fid}: Elektrik emisyon faktörü çok yüksek görünüyor (kgCO2/kWh).")

        out = run_biolot(**inp)

        # audit log
        run_id = str(uuid.uuid4())
        append_audit_log(run_id, str(BIOL0T_ENGINE_VERSION), facility_id=fid, inputs=inp, outputs=out)

        # add facility result
        portfolio["facilities"].append({
            "facility_id": fid,
            "run_id": run_id,
            "inputs": inp,
            "outputs": out,
        })

        # totals
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

# -------------------------------
# SHOW PORTFOLIO RESULT
# -------------------------------
portfolio = st.session_state.get("portfolio_result")

if portfolio:
    totals = portfolio["portfolio_totals"]

    st.subheader("Portfolio Toplamları")
    a1, a2, a3 = st.columns(3)
    a1.metric("Toplam Scope 1 (ton/yıl)", f"{totals['scope1_ton']:.2f}")
    a2.metric("Toplam Scope 2 (ton/yıl)", f"{totals['scope2_ton']:.2f}")
    a3.metric("Toplam Emisyon (ton/yıl)", f"{totals['total_ton']:.2f}")

    b1, b2, b3 = st.columns(3)
    b1.metric("Toplam Enerji Tasarrufu (kWh/yıl)", f"{totals['total_saved_kwh']:.0f}")
    b2.metric("Toplam Önlenen CO2 (ton/yıl)", f"{totals['total_saved_co2_ton']:.3f}")
    b3.metric("Toplam Kaçınılan Maliyet (€ / yıl)", f"{totals['total_saved_eur']:.2f}")

    st.divider()

    with st.expander("Portfolio JSON (Denetlenebilir Çıktı)"):
        st.json(portfolio)

        json_text = json.dumps(portfolio, ensure_ascii=False, indent=2, sort_keys=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"biolot_portfolio_v{BIOL0T_ENGINE_VERSION}_{ts}.json"

        st.download_button(
            label="⬇️ Portfolio JSON'u indir",
            data=json_text.encode("utf-8"),
            file_name=filename,
            mime="application/json",
            use_container_width=True,
        )

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
        st.caption("runs.jsonl: Her satır bir tesis koşusunun audit kaydıdır (append-only).")
else:
    st.info("Tesisleri ekleyip girdileri düzenledikten sonra 'Tüm Tesisleri Çalıştır' bas.")
