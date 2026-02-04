from fastmcp import FastMCP
import uuid
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("restaurant-booking")

mcp = FastMCP("restaurant-booking")

logger.info("🍽️ Restaurant booking MCP server initialized")

RESTAURANTS = {
    "bachevski": {
        "name": "Baczewski",
        "city": "Lviv",
        "address": "8 Shevska Str.",
        "tables": [
            {"id": 1, "seats": 2},
            {"id": 2, "seats": 4},
            {"id": 3, "seats": 6},
            {"id": 4, "seats": 8},
        ],
        "working_hours": {"open": "10:00", "close": "23:00"},
    },
    "kryivka": {
        "name": "Kryivka",
        "city": "Lviv",
        "address": "14 Rynok Sq.",
        "tables": [
            {"id": 1, "seats": 4},
            {"id": 2, "seats": 4},
            {"id": 3, "seats": 6},
        ],
        "working_hours": {"open": "12:00", "close": "00:00"},
    },
}

RESERVATIONS: dict[str, dict] = {}

def _booking_key(restaurant: str, date: str, time: str, table_id: int) -> str:
    return f"{restaurant}_{date}_{time}_{table_id}"

@mcp.tool()
def check_availability(
    restaurant: str,
    date: str,
    time: str,
    guests: int,
) -> dict:
    logger.info("🔍 check_availability | %s %s %s %s",
                restaurant, date, time, guests)

    return _check_availability_logic(
        restaurant=restaurant,
        date=date,
        time=time,
        guests=guests,
    )

@mcp.tool()
def make_reservation(
    restaurant: str,
    date: str,
    time: str,
    guests: int,
    name: str,
    phone: str,
) -> dict:
    logger.info(
        "📝 make_reservation | restaurant=%s date=%s time=%s guests=%s name=%s",
        restaurant, date, time, guests, name,
    )

    availability = _check_availability_logic(
        restaurant=restaurant,
        date=date,
        time=time,
        guests=guests,
    )

    if not availability.get("available"):
        logger.warning(
            "❌ No availability | restaurant=%s date=%s time=%s",
            restaurant, date, time,
        )
        return {
            "status": "failed",
            "error": "No tables available at this time",
        }

    table = availability["tables"][0]
    reservation_id = f"RES-{date.replace('-', '')}-{uuid.uuid4().hex[:4].upper()}"

    reservation = {
        "reservation_id": reservation_id,
        "restaurant": restaurant,
        "restaurant_name": RESTAURANTS[restaurant]["name"],
        "address": RESTAURANTS[restaurant]["address"],
        "date": date,
        "time": time,
        "guests": guests,
        "table_id": table["id"],
        "name": name,
        "phone": phone,
        "status": "confirmed",
    }

    RESERVATIONS[_booking_key(restaurant, date, time, table["id"])] = reservation
    RESERVATIONS[reservation_id] = reservation

    logger.info(
        "🎉 Reservation confirmed | id=%s restaurant=%s table=%s",
        reservation_id, restaurant, table["id"],
    )

    return {
        "status": "confirmed",
        "reservation_id": reservation_id,
        "details": {
            "restaurant": reservation["restaurant_name"],
            "address": reservation["address"],
            "date": date,
            "time": time,
            "guests": guests,
            "table": table["id"],
        },
    }


@mcp.tool()
def cancel_reservation(reservation_id: str) -> dict:
    logger.info("🗑 cancel_reservation | id=%s", reservation_id)

    if reservation_id not in RESERVATIONS:
        logger.warning("❌ Reservation not found | id=%s", reservation_id)
        return {
            "status": "failed",
            "error": f"Reservation '{reservation_id}' not found",
        }

    reservation = RESERVATIONS[reservation_id]
    key = _booking_key(
        reservation["restaurant"],
        reservation["date"],
        reservation["time"],
        reservation["table_id"],
    )

    RESERVATIONS.pop(key, None)
    RESERVATIONS.pop(reservation_id, None)

    logger.info("✅ Reservation cancelled | id=%s", reservation_id)

    return {
        "status": "cancelled",
        "message": f"Reservation {reservation_id} successfully cancelled",
    }


@mcp.tool()
def list_reservations(phone: str) -> dict:
    logger.info("📋 list_reservations | phone=%s", phone)

    reservations = [
        res
        for res in RESERVATIONS.values()
        if isinstance(res, dict) and res.get("phone") == phone
    ]

    return {
        "count": len(reservations),
        "reservations": reservations,
    }

@mcp.resource("restaurants://list")
def list_restaurants() -> str:
    logger.info("📖 list_restaurants resource requested")

    result = "# Available Restaurants\n\n"

    for key, rest in RESTAURANTS.items():
        result += f"## {rest['name']} ({key})\n"
        result += f"- City: {rest['city']}\n"
        result += f"- Address: {rest['address']}\n"
        result += (
            f"- Hours: "
            f"{rest['working_hours']['open']} - "
            f"{rest['working_hours']['close']}\n\n"
        )

    return result

def _check_availability_logic(
    restaurant: str,
    date: str,
    time: str,
    guests: int,
) -> dict:
    if restaurant not in RESTAURANTS:
        return {
            "available": False,
            "error": f"Restaurant '{restaurant}' not found",
        }

    rest = RESTAURANTS[restaurant]

    available_tables = [
        table
        for table in rest["tables"]
        if table["seats"] >= guests
        and _booking_key(restaurant, date, time, table["id"]) not in RESERVATIONS
    ]

    return {
        "available": len(available_tables) > 0,
        "restaurant": rest["name"],
        "date": date,
        "time": time,
        "tables": available_tables,
    }

if __name__ == "__main__":
    logger.info("🚀 Starting Restaurant Booking MCP server...")
    mcp.run(transport="stdio")