import random
import requests
import streamlit as st

st.set_page_config(page_title="Tomato Leaf Monitor", page_icon="🍅")
st.title("🍅 Tomato Leaf Monitor")

demo = st.toggle("Demo mode (dummy data)", value=True)

try:
    FIREBASE_URL = st.secrets["FIREBASE_URL"]
except Exception:
    FIREBASE_URL = ""

def get_data():
    if demo or not FIREBASE_URL:
        return {
            "temperature": round(random.uniform(24, 32), 1),
            "humidity": random.randint(55, 80),
            "soil_moisture": random.randint(30, 60),
            "rain": random.choice([0, 1]),
            "disease": random.choice(["Healthy", "Early Blight", "Leaf Miner"]),
            "confidence": round(random.uniform(0.8, 0.98), 2),
        }
    try:
        return requests.get(f"{FIREBASE_URL}/latest.json", timeout=5).json()
    except Exception:
        return None

@st.fragment(run_every=5)
def show():
    d = get_data()
    if not d:
        st.error("No data received")
        return
    c1, c2 = st.columns(2)
    c1.metric("Temperature", f"{d['temperature']} °C")
    c2.metric("Humidity", f"{d['humidity']} %")
    c3, c4 = st.columns(2)
    c3.metric("Soil moisture", f"{d['soil_moisture']} %")
    c4.metric("Rain", "Yes" if d["rain"] else "No")
    if d["disease"] == "Healthy":
        st.success(f"Plant looks healthy ({d['confidence']:.0%})")
    else:
        st.warning(f"{d['disease']} detected ({d['confidence']:.0%})")

show()
