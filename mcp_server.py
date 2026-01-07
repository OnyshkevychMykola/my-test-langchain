import os
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

app = FastMCP(name="Demo MCP Server")

@app.tool()
def multiply(a: float, b: float) -> dict:
    """
    Multiply two numbers.

    Use this tool ONLY for numeric multiplication.
    Both inputs must be valid numbers.

    Returns the multiplication result.
    """
    try:
        return {
            "a": a,
            "b": b,
            "result": a * b
        }
    except Exception as e:
        return {
            "error": "math_error",
            "message": str(e)
        }


@app.tool()
def get_weather(city: str) -> dict:
    """
    Get current weather for a real city.

    Use this tool ONLY when the user explicitly asks about weather conditions.
    City must be a real city name (e.g. "Kyiv", "Toronto").
    Do NOT guess the city.

    Returns temperature in Celsius and a short weather description.
    """
    if not city or len(city) > 50:
        return {
            "error": "invalid_city",
            "message": "City name is empty or too long."
        }

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "appid": WEATHER_API_KEY,
                "units": "metric",
                "lang": "uk",
            },
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        return {
            "city": city,
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"],
        }

    except requests.HTTPError:
        return {
            "error": "weather_not_found",
            "message": f"Weather data for '{city}' was not found."
        }

    except requests.RequestException as e:
        return {
            "error": "weather_api_unavailable",
            "message": str(e)
        }


if __name__ == "__main__":
    app.run(transport="streamable-http")