import os
import datetime
import streamlit as st
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

load_dotenv()

INFLUXDB_URL = os.getenv("LOCAL_INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "top-secret-token-123")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "my-org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "nutrition-stats")

st.set_page_config(page_title="Edit Records", page_icon="✏️")
st.title("✏️ Edit Records")


@st.cache_data(ttl=30)
def fetch_meals(days: int) -> list[dict]:
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query = f"""
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -{days}d)
  |> filter(fn: (r) => r._measurement == "nutrition")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
"""
    tables = client.query_api().query(query)
    client.close()

    meals = []
    for table in tables:
        for record in table.records:
            t = record.get_time().replace(tzinfo=None)
            meals.append({
                "_time_utc": record.get_time(),
                "_time_local": t,
                "label": f"{t.strftime('%Y-%m-%d %H:%M')}  |  {record.values.get('type', '')} — {record.values.get('name', '')}",
                "name": record.values.get("name", ""),
                "type": record.values.get("type", ""),
                "category": record.values.get("category", ""),
                "source": record.values.get("source", ""),
                "kcal": float(record.values.get("kcal", 0)),
                "protein": float(record.values.get("protein", 0)),
                "fat": float(record.values.get("fat", 0)),
                "fat_sat": float(record.values.get("fat_sat", 0)),
                "carbs": float(record.values.get("carbs", 0)),
                "sugars": float(record.values.get("sugars", 0)),
                "salt": float(record.values.get("salt", 0)),
            })
    meals.sort(key=lambda m: m["_time_utc"], reverse=True)
    return meals


def save_record(old_utc: datetime.datetime, new_data: dict):
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

    # Delete the old point using a 1-second window around its timestamp
    delete_api = client.delete_api()
    delete_api.delete(
        old_utc - datetime.timedelta(seconds=1),
        old_utc + datetime.timedelta(seconds=1),
        '_measurement="nutrition"',
        bucket=INFLUXDB_BUCKET,
        org=INFLUXDB_ORG,
    )

    # Write corrected point
    point = (
        Point("nutrition")
        .tag("type", new_data["type"])
        .tag("category", new_data["category"])
        .tag("source", new_data["source"])
        .field("name", new_data["name"])
        .field("kcal", new_data["kcal"])
        .field("protein", new_data["protein"])
        .field("fat", new_data["fat"])
        .field("fat_sat", new_data["fat_sat"])
        .field("carbs", new_data["carbs"])
        .field("sugars", new_data["sugars"])
        .field("salt", new_data["salt"])
        .time(new_data["log_time"], WritePrecision.S)
    )
    client.write_api(write_options=SYNCHRONOUS).write(bucket=INFLUXDB_BUCKET, record=point)
    client.close()


# ── Sidebar controls ──────────────────────────────────────────────────────────

days = st.sidebar.slider("Show last N days", min_value=1, max_value=30, value=5)
if st.sidebar.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# ── Load meals ────────────────────────────────────────────────────────────────

meals = fetch_meals(days)

if not meals:
    st.info("No meals found for the selected period.")
    st.stop()

# ── Meal selector ─────────────────────────────────────────────────────────────

labels = [m["label"] for m in meals]
selected_label = st.selectbox("Select a meal to edit", labels)
meal = meals[labels.index(selected_label)]

st.divider()

# ── Edit form ─────────────────────────────────────────────────────────────────

with st.form("edit_form"):
    st.subheader("General Information")

    meal_name = st.text_input("Meal Name", value=meal["name"])

    col_a, col_b, col_c = st.columns(3)
    meal_type = col_a.selectbox(
        "Meal Type", ["Breakfast", "II Breakfast", "Lunch", "Snack", "Dinner"],
        index=["Breakfast", "II Breakfast", "Lunch", "Snack", "Dinner"].index(meal["type"])
        if meal["type"] in ["Breakfast", "II Breakfast", "Lunch", "Snack", "Dinner"] else 0,
    )
    category = col_b.selectbox(
        "Category", ["catering", "home", "restaurant", "cheat"],
        index=["catering", "home", "restaurant", "cheat"].index(meal["category"])
        if meal["category"] in ["catering", "home", "restaurant", "cheat"] else 0,
    )
    source = col_c.selectbox(
        "Source", ["Brokul", "Homemade", "Store", "Restaurant"],
        index=["Brokul", "Homemade", "Store", "Restaurant"].index(meal["source"])
        if meal["source"] in ["Brokul", "Homemade", "Store", "Restaurant"] else 0,
    )

    st.divider()
    st.subheader("Date & Time")

    col_date, col_time = st.columns(2)
    new_date = col_date.date_input("Date", value=meal["_time_local"].date())
    new_time = col_time.time_input("Time", value=meal["_time_local"].time())

    st.divider()
    st.subheader("Nutritional Values")

    col1, col2, col3, col4 = st.columns(4)
    kcal = col1.number_input("kcal", min_value=0.0, step=1.0, value=meal["kcal"])
    fat = col2.number_input("Total Fat (g)", min_value=0.0, step=0.1, value=meal["fat"])
    fat_sat = col3.number_input("Sat. Fat (g)", min_value=0.0, step=0.1, value=meal["fat_sat"])
    carb = col4.number_input("Carbs (g)", min_value=0.0, step=0.1, value=meal["carbs"])

    col5, col6, col7 = st.columns(3)
    sugars = col5.number_input("Sugars (g)", min_value=0.0, step=0.1, value=meal["sugars"])
    prot = col6.number_input("Protein (g)", min_value=0.0, step=0.1, value=meal["protein"])
    salt = col7.number_input("Salt (g)", min_value=0.0, step=0.01, value=meal["salt"])

    saved = st.form_submit_button("💾 Save Changes")

if saved:
    new_dt = datetime.datetime.combine(new_date, new_time)
    save_record(
        old_utc=meal["_time_utc"],
        new_data={
            "name": meal_name,
            "type": meal_type,
            "category": category,
            "source": source,
            "kcal": kcal,
            "protein": prot,
            "fat": fat,
            "fat_sat": fat_sat,
            "carbs": carb,
            "sugars": sugars,
            "salt": salt,
            "log_time": new_dt,
        },
    )
    st.success(f"✅ '{meal_name}' updated successfully!")
    st.cache_data.clear()
    st.rerun()