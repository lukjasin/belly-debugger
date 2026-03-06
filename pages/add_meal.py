import os
import datetime
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")
APP_NAME = os.getenv("APP_NAME", "Belly-Debugger")

st.title(f"📉 {APP_NAME}")
st.info("Input your meal data below to debug your belly.")


def _capture_meal_datetime():
    """Callback: runs on submit before clear_on_submit wipes widget values."""
    d = st.session_state["_meal_date"]
    t = st.session_state["_meal_time"]
    st.session_state["_meal_dt"] = datetime.datetime.combine(d, t)


with st.form("meal_entry_form", clear_on_submit=True):
    st.subheader("General Information")
    meal_name = st.text_input("Meal Name", placeholder="e.g., Chicken in Peanut Sauce")

    col_a, col_b, col_c = st.columns(3)
    meal_type = col_a.selectbox("Meal Type", ["Breakfast", "II Breakfast", "Lunch", "Snack", "Dinner"])
    category = col_b.selectbox("Category", ["catering", "home", "restaurant", "cheat"])
    source = col_c.selectbox("Source", ["Brokul", "Homemade", "Store", "Restaurant"])

    st.divider()
    st.subheader("Time Travel")
    col_date, col_time = st.columns(2)
    d = col_date.date_input("Date", datetime.date.today(), key="_meal_date")
    t = col_time.time_input("Time", datetime.datetime.now().time(), key="_meal_time")

    st.divider()
    st.subheader("Nutritional Values (Base)")
    st.caption("Enter values from the label (per box) or per 100g for manual weighing.")

    col1, col2, col3, col4 = st.columns(4)
    kcal = col1.number_input("kcal", min_value=0.0, step=1.0)
    fat = col2.number_input("Total Fat (g)", min_value=0.0, step=0.1)
    fat_sat = col3.number_input("Sat. Fat (g)", min_value=0.0, step=0.1)
    carb = col4.number_input("Carbs (g)", min_value=0.0, step=0.1)

    col5, col6, col7 = st.columns(3)
    sugars = col5.number_input("Sugars (g)", min_value=0.0, step=0.1)
    prot = col6.number_input("Protein (g)", min_value=0.0, step=0.1)
    salt = col7.number_input("Salt (g)", min_value=0.0, step=0.01)

    st.divider()
    st.subheader("Weight Logic")
    is_weighted = st.checkbox("Calculate based on weight (Weekend/Manual Mode)")

    weight_col1, weight_col2 = st.columns(2)
    weight_consumed = weight_col1.number_input("Weight Consumed (g)", min_value=0.0, step=1.0, value=0.0)
    reference_size = weight_col2.number_input("Reference Size (g)", min_value=1.0, step=10.0, value=100.0)

    ready_to_send = st.checkbox("Ready to log this meal?")
    submitted = st.form_submit_button("Commit to Database", on_click=_capture_meal_datetime)

if submitted:
    if not ready_to_send:
        st.warning("Please check 'Ready to log' before submitting!")
    else:
        payload = {
            "meal_name": meal_name,
            "meal_type": meal_type,
            "category": category,
            "source": source,
            "kcal_base": kcal,
            "protein_base": prot,
            "fat_total_base": fat,
            "fat_saturated_base": fat_sat,
            "carbs_total_base": carb,
            "sugars_base": sugars,
            "salt_base": salt,
            "is_weighted": is_weighted,
            "weight_consumed_g": weight_consumed if is_weighted else None,
            "reference_size_g": reference_size,
            "log_time": st.session_state["_meal_dt"].isoformat()
        }

        try:
            response = requests.post(f"{API_URL}/log-meal", json=payload)
            if response.status_code == 200:
                st.success(f"Success! {meal_name} logged correctly.")
                st.balloons()
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"🔌 Could not connect to API: {e}")