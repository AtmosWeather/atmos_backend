import os
import httpx
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


@router.get("/current")
async def get_current_weather(city: str = Query(..., description="City name")):
    """Proxy to OpenWeatherMap current-weather endpoint."""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenWeather API key not configured")

    url = f"{OPENWEATHER_BASE}/weather"
    params = {"q": city, "units": "metric", "appid": OPENWEATHER_API_KEY}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10.0)

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="City not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch weather data")

    return resp.json()


@router.get("/forecast")
async def get_forecast(city: str = Query(..., description="City name")):
    """Proxy to OpenWeatherMap 5-day/3-hour forecast endpoint."""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenWeather API key not configured")

    url = f"{OPENWEATHER_BASE}/forecast"
    params = {"q": city, "units": "metric", "appid": OPENWEATHER_API_KEY}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10.0)

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="City not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch forecast data")

    return resp.json()
