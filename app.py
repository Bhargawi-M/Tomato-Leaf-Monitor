import requests
import streamlit as st

st.set_page_config(page_title="Tomato Leaf Monitor", page_icon="🍅")

TXT = {
    "en": {
        "title": "Tomato Leaf Monitor",
        "temp": "Temperature", "hum": "Humidity", "soil": "Soil moisture",
        "rain": "Rain", "yes": "Yes", "no": "No",
        "healthy": "Plant looks healthy", "detected": "detected",
        "water_now": "Water now", "ok": "Soil moisture OK",
        "too_wet": "Too wet, hold watering", "skip": "Rain detected, skip watering",
        "risk": "Fungal disease risk", "Low": "Low", "Medium": "Medium", "High": "High",
        "nodata": "No data received",
        "note": "Risk and watering are simple rule-based indicators, not a trained model.",
    },
    "kn": {
        "title": "ಟೊಮೆಟೊ ಎಲೆ ಮಾನಿಟರ್",
        "temp": "ತಾಪಮಾನ", "hum": "ಆರ್ದ್ರತೆ", "soil": "ಮಣ್ಣಿನ ತೇವಾಂಶ",
        "rain": "ಮಳೆ", "yes": "ಹೌದು", "no": "ಇಲ್ಲ",
        "healthy": "ಸಸ್ಯ ಆರೋಗ್ಯವಾಗಿದೆ", "detected": "ಪತ್ತೆಯಾಗಿದೆ",
        "water_now": "ಈಗ ನೀರು ಹಾಕಿ", "ok": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಸರಿಯಾಗಿದೆ",
        "too_wet": "ತುಂಬಾ ಒದ್ದೆ, ನೀರು ಹಾಕಬೇಡಿ", "skip": "ಮಳೆ ಬಂದಿದೆ, ನೀರು ಹಾಕಬೇಡಿ",
        "risk": "ಶಿಲೀಂಧ್ರ ರೋಗದ ಅಪಾಯ", "Low": "ಕಡಿಮೆ", "Medium": "ಮಧ್ಯಮ", "High": "ಹೆಚ್ಚು",
        "nodata": "ಡೇಟಾ ಬಂದಿಲ್ಲ",
        "note": "ಅಪಾಯ ಮತ್ತು ನೀರಾವರಿ ಸರಳ ನಿಯಮ-ಆಧಾರಿತ ಸೂಚಕಗಳು.",
    },
}

try:
    URL = st.secrets["FIREBASE_URL"]
except Exception:
    URL = ""


def get_latest():
    try:
        return requests.get(f"{URL}/latest.json", timeout=5).json()
    except Exception:
        return None


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


@st.fragment(run_every=10)
def show(L):
    d = get_latest()
    if not d:
        st.error(L["nodata"])
        return

    disease = d.get("disease")
    conf = num(d, "confidence")
    pct = f" ({conf:.0%})" if conf is not None else ""
    rk, ir = risk(d), irrigation(d)

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


kn = st.toggle("ಕನ್ನಡ", key="kn")
L = TXT["kn" if kn else "en"]
st.title("🍅 " + L["title"])
if not URL:
    st.error("FIREBASE_URL is not set in the app's secrets.")
else:
    show(L)
