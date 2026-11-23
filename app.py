import base64
import os

import numpy as np
import requests
import streamlit as st
from PIL import Image
try:
    import tensorflow as tf
    HAS_TF = True
except Exception:
    HAS_TF = False

st.set_page_config(page_title="Tomato Leaf Monitor", page_icon="🍅")

MODEL_PATH = "teammate_model.keras"
CLASS_NAMES = ["Early_Blight", "Healthy", "Leaf_Miner"]
THRESHOLD = 0.50

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
        "check": "Check a leaf photo",
        "upload": "Upload a leaf photo",
        "camera": "Or take a photo",
        "nomodel": "The photo checker needs the model file and TensorFlow, which this deployment does not have. Run the app on the laptop that has them.",
        "low": "Low confidence, so no result is shown. Try a clearer close-up of one leaf.",
        "send": "Send result to dashboard",
        "sent": "Sent. The live view updates in a few seconds.",
        "fail": "Could not send the result",
        "probs": "Model probabilities",
        "photo": "Latest photo from the leaf camera",
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
        "check": "ಎಲೆಯ ಫೋಟೋ ಪರೀಕ್ಷಿಸಿ",
        "upload": "ಎಲೆಯ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
        "camera": "ಅಥವಾ ಫೋಟೋ ತೆಗೆಯಿರಿ",
        "nomodel": "ಈ ಸೌಲಭ್ಯಕ್ಕೆ ಮಾದರಿ ಫೈಲ್ ಮತ್ತು TensorFlow ಬೇಕು.",
        "low": "ವಿಶ್ವಾಸ ಕಡಿಮೆ ಇದೆ. ಒಂದು ಎಲೆಯ ಸ್ಪಷ್ಟ ಹತ್ತಿರದ ಫೋಟೋ ಪ್ರಯತ್ನಿಸಿ.",
        "send": "ಫಲಿತಾಂಶವನ್ನು ಡ್ಯಾಶ್‌ಬೋರ್ಡ್‌ಗೆ ಕಳುಹಿಸಿ",
        "sent": "ಕಳುಹಿಸಲಾಗಿದೆ.",
        "fail": "ಫಲಿತಾಂಶ ಕಳುಹಿಸಲಾಗಲಿಲ್ಲ",
        "probs": "ಮಾದರಿಯ ಸಂಭಾವ್ಯತೆಗಳು",
        "photo": "ಎಲೆ ಕ್ಯಾಮೆರಾದ ಇತ್ತೀಚಿನ ಫೋಟೋ",
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


def get_image():
    try:
        r = requests.get(f"{URL}/latest_image.json", timeout=5).json()
        if r and r.get("image"):
            return base64.b64decode(r["image"]), r.get("time", "")
    except Exception:
        pass
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

    photo = get_image()
    if photo:
        st.image(photo[0], caption=f"{L['photo']} {photo[1]}", use_container_width=True)

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


@st.cache_resource
def load_model():
    return tf.keras.models.load_model(MODEL_PATH)


def predict(img):
    img = img.convert("RGB").resize((224, 224), Image.BILINEAR)
    x = np.expand_dims(np.array(img, dtype="float32"), 0)
    return load_model().predict(x, verbose=0)[0]


def photo_section(L):
    st.divider()
    st.subheader(L["check"])
    if not HAS_TF or not os.path.exists(MODEL_PATH):
        st.info(L["nomodel"])
        return

    photo = st.file_uploader(L["upload"], type=["jpg", "jpeg", "png", "jfif", "webp"])
    with st.expander(L["camera"]):
        cam = st.camera_input(L["camera"])
    file = photo or cam
    if not file:
        return

    img = Image.open(file)
    st.image(img, use_container_width=True)
    p = predict(img)
    i = int(np.argmax(p))
    label = CLASS_NAMES[i].replace("_", " ").title()
    conf = float(p[i])

    if conf < THRESHOLD:
        st.info(L["low"])
    elif label == "Healthy":
        st.success(f"{L['healthy']} ({conf:.0%})")
    else:
        st.warning(f"{label} {L['detected']} ({conf:.0%})")

    st.caption(L["probs"])
    for name, pr in zip(CLASS_NAMES, p):
        st.progress(float(pr), text=f"{name.replace('_', ' ')}: {pr:.0%}")

    if conf >= THRESHOLD and URL and st.button(L["send"]):
        try:
            r = requests.patch(f"{URL}/latest.json",
                               json={"disease": label, "confidence": round(conf, 2)},
                               timeout=5)
            if r.ok:
                st.success(L["sent"])
            else:
                st.error(f"{L['fail']} ({r.status_code})")
        except Exception:
            st.error(L["fail"])


kn = st.toggle("ಕನ್ನಡ", key="kn")
L = TXT["kn" if kn else "en"]
st.title("🍅 " + L["title"])
if not URL:
    st.error("FIREBASE_URL is not set in the app's secrets.")
else:
    show(L)
photo_section(L)
