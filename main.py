import os
from fastapi import FastAPI, HTTPException
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from models import MealEntry, WeightEntry
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()

app = FastAPI(title=os.getenv("APP_NAME"))

# InfluxDB Configuration
client = InfluxDBClient(
    url=os.getenv("INFLUXDB_URL"),
    token=os.getenv("INFLUXDB_TOKEN"),
    org=os.getenv("INFLUXDB_ORG")
)
write_api = client.write_api(write_options=SYNCHRONOUS)


@app.post("/log-weight")
async def log_weight(entry: WeightEntry):
    final_time = entry.log_time if entry.log_time else datetime.utcnow()

    point = Point("body_stats")
    if entry.weight is not None:
        point = point.field("weight", entry.weight)
    if entry.waist is not None:
        point = point.field("waist", entry.waist)
    if entry.chest is not None:
        point = point.field("chest", entry.chest)
    point = point.time(final_time, WritePrecision.S)

    write_api.write(bucket=os.getenv("INFLUXDB_BUCKET"), record=point)
    return {"status": "success"}

@app.post("/log-meal")
async def log_meal(entry: MealEntry):
    # Calculate multiplier for non-catering meals
    multiplier = 1.0
    if entry.is_weighted and entry.weight_consumed_g:
        multiplier = entry.weight_consumed_g / entry.reference_size_g

    # Take current datetime if not specified
    final_time = entry.log_time if entry.log_time else datetime.utcnow()

    # Prepare data point for Belly-Debugger
    point = Point("nutrition") \
        .tag("type", entry.meal_type) \
        .tag("category", entry.category) \
        .tag("source", entry.source) \
        .field("name", entry.meal_name) \
        .field("kcal", round(entry.kcal_base * multiplier, 1)) \
        .field("protein", round(entry.protein_base * multiplier, 1)) \
        .field("fat", round(entry.fat_total_base * multiplier, 1)) \
        .field("fat_sat", round(entry.fat_saturated_base * multiplier, 1)) \
        .field("carbs", round(entry.carbs_total_base * multiplier, 1)) \
        .field("sugars", round(entry.sugars_base * multiplier, 1)) \
        .field("salt", round(entry.salt_base * multiplier, 2)) \
        .time(final_time, WritePrecision.S)

    try:
        write_api.write(bucket=os.getenv("INFLUXDB_BUCKET"), record=point)
        return {"status": "success", "message": f"Meal {entry.meal_name} debugged!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("API_PORT")))