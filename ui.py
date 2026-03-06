import os
import datetime
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")
APP_NAME = os.getenv("APP_NAME", "Belly-Debugger")
INFLUXDB_URL = os.getenv("LOCAL_INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

app = FastAPI()
templates = Jinja2Templates(directory="templates")


def get_influx_client():
    return InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)


def fetch_meals(days: int) -> list[dict]:
    client = get_influx_client()
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
                "_time_utc_iso": record.get_time().isoformat(),
                "_time_local": t.strftime("%Y-%m-%dT%H:%M"),
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
    meals.sort(key=lambda m: m["_time_utc_iso"], reverse=True)
    return meals


def _ctx(request, **kwargs):
    return {"request": request, "app_name": APP_NAME, **kwargs}


# ── Add Meal ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
@app.get("/add-meal", response_class=HTMLResponse)
async def add_meal_page(request: Request):
    return templates.TemplateResponse("add_meal.html", _ctx(request))


@app.post("/add-meal", response_class=HTMLResponse)
async def add_meal_submit(request: Request):
    form = await request.form()

    log_dt = datetime.datetime.fromisoformat(
        f"{form['log_date']}T{form['log_time']}"
    )
    is_weighted = "is_weighted" in form
    weight_consumed = float(form.get("weight_consumed") or 0)
    reference_size = float(form.get("reference_size") or 100)

    payload = {
        "meal_name": form["meal_name"],
        "meal_type": form["meal_type"],
        "category": form["category"],
        "source": form["source"],
        "kcal_base": float(form.get("kcal") or 0),
        "protein_base": float(form.get("prot") or 0),
        "fat_total_base": float(form.get("fat") or 0),
        "fat_saturated_base": float(form.get("fat_sat") or 0),
        "carbs_total_base": float(form.get("carb") or 0),
        "sugars_base": float(form.get("sugars") or 0),
        "salt_base": float(form.get("salt") or 0),
        "is_weighted": is_weighted,
        "weight_consumed_g": weight_consumed if is_weighted else None,
        "reference_size_g": reference_size,
        "log_time": log_dt.isoformat(),
    }

    try:
        response = requests.post(f"{API_URL}/log-meal", json=payload)
        if response.status_code == 200:
            return templates.TemplateResponse("add_meal.html", _ctx(request, success=f"{form['meal_name']} logged!"))
        else:
            return templates.TemplateResponse("add_meal.html", _ctx(request, error=f"API error: {response.status_code}"))
    except Exception as e:
        return templates.TemplateResponse("add_meal.html", _ctx(request, error=str(e)))


# ── Body Weight ───────────────────────────────────────────────────────────────

@app.get("/body-weight", response_class=HTMLResponse)
async def body_weight_page(request: Request):
    return templates.TemplateResponse("body_weight.html", _ctx(request))


@app.post("/body-weight", response_class=HTMLResponse)
async def body_weight_submit(request: Request):
    form = await request.form()

    def opt_float(key):
        val = form.get(key, "").strip()
        return float(val) if val else None

    weight = opt_float("weight")
    waist = opt_float("waist")
    chest = opt_float("chest")

    if weight is None and waist is None and chest is None:
        return templates.TemplateResponse("body_weight.html", _ctx(request, error="Enter at least one measurement."))

    combined_dt = datetime.datetime.combine(
        datetime.date.fromisoformat(form["w_date"]),
        datetime.datetime.now().time(),
    )
    payload = {"log_time": combined_dt.isoformat()}
    if weight is not None:
        payload["weight"] = weight
    if waist is not None:
        payload["waist"] = waist
    if chest is not None:
        payload["chest"] = chest

    try:
        response = requests.post(f"{API_URL}/log-weight", json=payload)
        if response.status_code == 200:
            return templates.TemplateResponse("body_weight.html", _ctx(request, success="Measurements saved!"))
        else:
            return templates.TemplateResponse("body_weight.html", _ctx(request, error=f"API error: {response.status_code}"))
    except Exception as e:
        return templates.TemplateResponse("body_weight.html", _ctx(request, error=str(e)))


# ── Edit Records ──────────────────────────────────────────────────────────────

@app.get("/edit-records", response_class=HTMLResponse)
async def edit_records_page(request: Request, days: int = 5):
    meals = fetch_meals(days)
    return templates.TemplateResponse("edit_records.html", _ctx(request, meals=meals, days=days))


@app.post("/edit-records", response_class=HTMLResponse)
async def edit_records_submit(request: Request):
    form = await request.form()
    days = int(form.get("days", 5))

    old_utc = datetime.datetime.fromisoformat(form["old_time_utc"])
    new_dt = datetime.datetime.fromisoformat(f"{form['log_date']}T{form['log_time_val']}")

    client = get_influx_client()
    client.delete_api().delete(
        old_utc - datetime.timedelta(seconds=1),
        old_utc + datetime.timedelta(seconds=1),
        '_measurement="nutrition"',
        bucket=INFLUXDB_BUCKET,
        org=INFLUXDB_ORG,
    )

    point = (
        Point("nutrition")
        .tag("type", form["meal_type"])
        .tag("category", form["category"])
        .tag("source", form["source"])
        .field("name", form["meal_name"])
        .field("kcal", float(form.get("kcal") or 0))
        .field("protein", float(form.get("prot") or 0))
        .field("fat", float(form.get("fat") or 0))
        .field("fat_sat", float(form.get("fat_sat") or 0))
        .field("carbs", float(form.get("carb") or 0))
        .field("sugars", float(form.get("sugars") or 0))
        .field("salt", float(form.get("salt") or 0))
        .time(new_dt, WritePrecision.S)
    )
    client.write_api(write_options=SYNCHRONOUS).write(bucket=INFLUXDB_BUCKET, record=point)
    client.close()

    meals = fetch_meals(days)
    return templates.TemplateResponse("edit_records.html", _ctx(request, meals=meals, days=days, success=f"'{form['meal_name']}' updated!"))