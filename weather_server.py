import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
load_dotenv()
import os

WEATHER_API_KEY = os.environ["WEATHER_API_KEY"]

app = FastMCP(name="weather", port=8002)

@app.tool()
def get_weather(city: str) -> dict:
    """
    Get current weather for a real city.
    """
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

@app.resource("weather://supported-cities")
def supported_cities() -> dict:
    return {
        "cities": ["Kyiv", "Lviv", "Odesa", "Kharkiv", "Dnipro"]
    }

@app.prompt("weather_response")
def weather_prompt(city: str, temperature: float, description: str) -> str:
    return f"""
    Provide a friendly weather report.

    City: {city}
    Temperature: {temperature} °C
    Description: {description}

    Respond in Ukrainian.
    """

if __name__ == "__main__":
    app.run(transport="streamable-http")