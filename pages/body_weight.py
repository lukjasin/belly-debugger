import os
import datetime
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.title("⚖️ Register Body Weight")

with st.form("weight_form"):
    weight = st.number_input("Weight (kg)", min_value=40.0, max_value=200.0, step=0.1, value=None, placeholder="Optional")
    waist = st.number_input("Waist (cm)", min_value=40.0, max_value=200.0, step=0.5, value=None, placeholder="Optional")
    chest = st.number_input("Chest (cm)", min_value=40.0, max_value=200.0, step=0.5, value=None, placeholder="Optional")
    w_date = st.date_input("Date", datetime.date.today())
    w_submitted = st.form_submit_button("Save Weight")

if w_submitted:
    combined_w_datetime = datetime.datetime.combine(w_date, datetime.datetime.now().time())

    if weight is None and waist is None and chest is None:
        st.warning("Please enter at least one measurement.")
        st.stop()

    weight_payload = {"log_time": combined_w_datetime.isoformat()}
    if weight is not None:
        weight_payload["weight"] = weight
    if waist is not None:
        weight_payload["waist"] = waist
    if chest is not None:
        weight_payload["chest"] = chest

    try:
        response = requests.post(f"{API_URL}/log-weight", json=weight_payload)
        if response.status_code == 200:
            st.success(f"Weight {weight} kg saved!")
        else:
            st.error(f"API error: {response.status_code}")
    except Exception as e:
        st.error(f"🔌 Could not connect to API: {e}")