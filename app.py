import streamlit as st
import importlib

st.set_page_config(page_title="BIOLOT Demo", layout="wide")
st.title("BIOLOT — Web Demo")

st.sidebar.header("Girdiler (Demo)")
elec_kwh = st.sidebar.number_input("Elektrik (kWh/yıl)", min_value=0.0, value=8_500_000.0, step=100_000.0)
gas_m3 = st.sidebar.number_input("Doğalgaz (m³/yıl)", min_value=0.0, value=1_200_000.0, step=50_000.0)
water_m3 = st.sidebar.number_input("Su (m³/yıl)", min_value=0.0, value=45_000.0, step=1000.0)
carbon_price = st.sidebar.number_input("Karbon Fiyatı (€/tCO₂)", min_value=0.0, value=90.0, step=5.0)

st.divider()
st.subheader("Hesaplama")

run = st.button("Hesapla", type="primary")

if run:
    try:
        engine = importlib.import_module("engine")  # engine.py dosyasını çağırır

        # SENİN engine.py içinde hangi fonksiyon varsa burada onu çağıracağız.
        # Şimdilik sadece engine dosyasının yüklendiğini test ediyoruz:
        st.success("engine.py yüklendi ✅")

        # Burada bir sonraki adımda:
        # result = engine.calc_scope12(...)
        # st.json(result)

        st.info("Şimdi sıradaki adım: engine.py içindeki fonksiyon isimlerini bulup buraya bağlamak.")

    except Exception as e:
        st.error("engine.py çağrılamadı. Hata mesajı:")
        st.code(str(e))
