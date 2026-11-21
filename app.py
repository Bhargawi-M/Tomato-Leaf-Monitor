import random
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Tomato Leaf Monitor", page_icon="🍅")

TXT = {
    "en": {
        "title": "Tomato Leaf Monitor",
        "demo": "Demo mode (dummy data)",
        "live": "Live", "history": "History", "advice": "Advice",
        "temp": "Temperature", "hum": "Humidity", "soil": "Soil moisture",
        "rain": "Rain", "yes": "Yes", "no": "No",
        "healthy": "Plant looks healthy", "detected": "detected",
        "water_now": "Water now", "ok": "Soil moisture OK",
        "too_wet": "Too wet, hold watering", "skip": "Rain detected, skip watering",
        "risk": "Fungal disease risk", "Low": "Low", "Medium": "Medium", "High": "High",
        "nodata": "No data received", "no_hist": "No history yet",
        "report": "Download report",
        "note": "Risk and watering are simple rule-based indicators, not a trained model.",
    },
    "kn": {
        "title": "ಟೊಮೆಟೊ ಎಲೆ ಮಾನಿಟರ್",
        "demo": "ಡೆಮೊ ಮೋಡ್ (ಮಾದರಿ ಡೇಟಾ)",
        "live": "ನೇರ", "history": "ಇತಿಹಾಸ", "advice": "ಸಲಹೆ",
        "temp": "ತಾಪಮಾನ", "hum": "ಆರ್ದ್ರತೆ", "soil": "ಮಣ್ಣಿನ ತೇವಾಂಶ",
        "rain": "ಮಳೆ", "yes": "ಹೌದು", "no": "ಇಲ್ಲ",
        "healthy": "ಸಸ್ಯ ಆರೋಗ್ಯವಾಗಿದೆ", "detected": "ಪತ್ತೆಯಾಗಿದೆ",
        "water_now": "ಈಗ ನೀರು ಹಾಕಿ", "ok": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಸರಿಯಾಗಿದೆ",
        "too_wet": "ತುಂಬಾ ಒದ್ದೆ, ನೀರು ಹಾಕಬೇಡಿ", "skip": "ಮಳೆ ಬಂದಿದೆ, ನೀರು ಹಾಕಬೇಡಿ",
        "risk": "ಶಿಲೀಂಧ್ರ ರೋಗದ ಅಪಾಯ", "Low": "ಕಡಿಮೆ", "Medium": "ಮಧ್ಯಮ", "High": "ಹೆಚ್ಚು",
        "nodata": "ಡೇಟಾ ಬಂದಿಲ್ಲ", "no_hist": "ಇನ್ನೂ ಇತಿಹಾಸವಿಲ್ಲ",
        "report": "ವರದಿ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ",
        "note": "ಅಪಾಯ ಮತ್ತು ನೀರಾವರಿ ಸರಳ ನಿಯಮ-ಆಧಾರಿತ ಸೂಚಕಗಳು.",
    },
}

ADVICE = {
    "Healthy": "No disease detected. Keep monitoring, water at the base of the plant, and keep leaves dry.",
    "Early Blight": "Remove affected lower leaves, avoid overhead watering, and give the plants space for airflow.",
    "Leaf Miner": "Remove and destroy badly mined leaves and check the underside of leaves regularly.",
}
GENERIC = "Isolate and inspect the affected plant, and remove badly affected leaves."
DISCLAIMER = "Before using any pesticide or fungicide, consult a local agriculture officer."

try:
    URL = st.secrets["FIREBASE_URL"]
except Exception:
    URL = ""


def fake_reading():
    return {
        "temperature": round(random.uniform(24, 32), 1),
        "humidity": random.randint(55, 90),
        "soil_moisture": random.randint(20, 80),
        "rain": random.choice([0, 0, 1]),
        "disease": random.choice(["Healthy", "Early Blight", "Leaf Miner"]),
        "confidence": round(random.uniform(0.8, 0.98), 2),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def get_latest(demo):
    if demo or not URL:
        return fake_reading()
    try:
        return requests.get(f"{URL}/latest.json", timeout=5).json()
    except Exception:
        return None


def get_history(demo):
    if demo or not URL:
        rows = [fake_reading() for _ in range(20)]
    else:
        try:
            r = requests.get(
                f"{URL}/history.json",
                params={"orderBy": '"$key"', "limitToLast": 50},
                timeout=5,
            ).json()
            rows = list(r.values()) if r else []
        except Exception:
            rows = []
    return pd.DataFrame(rows)


def num(d, k):
    v = d.get(k)
    return v if isinstance(v, (int, float)) else None


def fmt(v, unit):
    return "--" if v is None else f"{v} {unit}"


def risk(d):
    h, t = num(d, "humidity"), num(d, "temperature")
    if h is None or t is None:
        return None
    if h >= 80 and 20 <= t <= 30:
        return "High"
    if h >= 65:
        return "Medium"
    return "Low"


def irrigation(d):
    if d.get("rain") == 1:
        return "skip"
    s = num(d, "soil_moisture")
    if s is None:
        return None
    if s < 30:
        return "water_now"
    if s > 70:
        return "too_wet"
    return "ok"


@st.fragment(run_every=5)
def show(demo, L):
    d = get_latest(demo)
    if not d:
        st.error(L["nodata"])
        return

    tab1, tab2, tab3 = st.tabs([L["live"], L["history"], L["advice"]])
    disease = d.get("disease")
    conf = num(d, "confidence")
    pct = f" ({conf:.0%})" if conf is not None else ""
    rk, ir = risk(d), irrigation(d)

    with tab1:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            c1.metric(L["temp"], fmt(num(d, "temperature"), "°C"))
            c2.metric(L["hum"], fmt(num(d, "humidity"), "%"))
            c3, c4 = st.columns(2)
            c3.metric(L["soil"], fmt(num(d, "soil_moisture"), "%"))
            c4.metric(L["rain"], L["yes"] if d.get("rain") == 1 else L["no"])
        if disease:
            if disease == "Healthy":
                st.success(L["healthy"] + pct)
            else:
                st.warning(f"{disease} {L['detected']}{pct}")
        if ir:
            {"ok": st.success, "water_now": st.warning,
             "too_wet": st.warning, "skip": st.info}[ir](L[ir])
        if rk:
            st.metric(L["risk"], L[rk])
        st.caption(L["note"])
        st.caption(str(d.get("timestamp", "")))

    with tab2:
        df = get_history(demo)
        cols = [c for c in ["temperature", "humidity", "soil_moisture"] if c in df.columns]
        if df.empty or not cols:
            st.info(L["no_hist"])
        else:
            st.line_chart(df[cols])
            st.dataframe(df[cols].describe().loc[["min", "mean", "max"]].round(1))

    with tab3:
        tip = ADVICE.get(disease, GENERIC) if disease else GENERIC
        st.write(tip)
        st.write(DISCLAIMER)
        report = "\n".join([
            "Tomato Leaf Monitor report",
            f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
            f"Disease: {disease} {pct}",
            f"Temperature: {fmt(num(d, 'temperature'), 'C')}",
            f"Humidity: {fmt(num(d, 'humidity'), '%')}",
            f"Soil moisture: {fmt(num(d, 'soil_moisture'), '%')}",
            f"Rain: {d.get('rain')}",
            f"Fungal disease risk: {rk}",
            f"Watering status: {ir}",
            f"Advice: {tip} {DISCLAIMER}",
        ])
        st.download_button(L["report"], report, file_name="tomato_report.txt")


kn = st.toggle("ಕನ್ನಡ", key="kn")
L = TXT["kn" if kn else "en"]
st.title("🍅 " + L["title"])
demo = st.toggle(L["demo"], value=True, key="demo")
show(demo, L)
