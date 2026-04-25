import os
import httpx
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


@router.get("/current")
async def get_current_weather(
    city: str = Query(None, description="City name"),
    lat: float = Query(None, description="Latitude"),
    lon: float = Query(None, description="Longitude")
):
    """Proxy to OpenWeatherMap current-weather endpoint."""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenWeather API key not configured")

    url = f"{OPENWEATHER_BASE}/weather"
    params = {"units": "metric", "appid": OPENWEATHER_API_KEY}
    
    if city:
        params["q"] = city
    elif lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
    else:
        raise HTTPException(status_code=400, detail="Must provide either city or both lat and lon")

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10.0)

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="City not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch weather data")

    return resp.json()


@router.get("/forecast")
async def get_forecast(
    city: str = Query(None, description="City name"),
    lat: float = Query(None, description="Latitude"),
    lon: float = Query(None, description="Longitude")
):
    """Proxy to OpenWeatherMap 5-day/3-hour forecast endpoint."""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenWeather API key not configured")

    url = f"{OPENWEATHER_BASE}/forecast"
    params = {"units": "metric", "appid": OPENWEATHER_API_KEY}
    
    if city:
        params["q"] = city
    elif lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
    else:
        raise HTTPException(status_code=400, detail="Must provide either city or both lat and lon")

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10.0)

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="City not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch forecast data")

    return resp.json()
