import streamlit as st

st.set_page_config(page_title="BIOLOT Demo", layout="wide")

st.title("BIOLOT — Test")
st.write("Eğer bu yazıyı görüyorsan uygulama çalışıyor ✅")

st.sidebar.header("Sidebar test")
x = st.sidebar.number_input("Test sayı", value=1.0)

st.subheader("Buton test")
clicked = st.button("Hesapla", type="primary")

st.write("Butona basıldı mı?:", clicked)
st.write("Sidebar değeri:", x)
