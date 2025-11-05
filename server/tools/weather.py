import httpx
from typing import Dict, Any, Optional

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherError(Exception):
    """Domain-level error for weather tool."""


async def geocode_city(client: httpx.AsyncClient, city: str) -> Dict[str, float | str]:
    """Resolve a city name to its latitude/longitude using Open-Meteo geocoding."""
    if not city or not city.strip():
        raise WeatherError("City is required.")
    params = {"name": city, "count": 1}
    resp = await client.get(GEOCODE_URL, params=params, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results") or []
    if not results:
        raise WeatherError(f"City not found: {city}")
    top = results[0]
    return {
        "lat": float(top["latitude"]),
        "lon": float(top["longitude"]),
        "name": str(top["name"]),
        "country": str(top.get("country", "")),
    }


async def fetch_current_weather(
    client: httpx.AsyncClient, lat: float, lon: float
) -> Dict[str, Any]:
    """Fetch current weather for given coordinates from Open-Meteo."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
    }
    resp = await client.get(FORECAST_URL, params=params, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    cw: Optional[Dict[str, Any]] = data.get("current_weather")
    if not cw:
        raise WeatherError("Current weather not available.")
    return cw


async def get_weather_for_city(city: str) -> Dict[str, Any]:
    """High-level function: geocode city, then fetch current weather."""
    async with httpx.AsyncClient() as client:
        info = await geocode_city(client, city)
        cw = await fetch_current_weather(client, float(info["lat"]), float(info["lon"]))
        return {
            "city": info["name"],
            "country": info["country"],
            "coords": {"lat": info["lat"], "lon": info["lon"]},
            "current_weather": cw,
        }
