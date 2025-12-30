import json
import os
from typing import Optional, Tuple

import dotenv
import mysql.connector

dotenv.load_dotenv()


def load_scraped_data(file_path: str):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("scraped data must be a list of station objects")
    return data


def parse_city(city: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Best-effort parser for 'City - Municipality' strings."""
    if not city:
        return None, None
    parts = [part.strip() for part in city.split("-") if part.strip()]
    if not parts:
        return None, None
    municipality = parts[-1]
    province = parts[0] if len(parts) > 1 else municipality
    return municipality, province


def get_or_create_municipality(cursor, municipality_name: Optional[str], province_name: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    if not municipality_name:
        return None, None

    cursor.execute(
        "SELECT municipality_id, province_id FROM Municipalities WHERE municipality_name = %s",
        (municipality_name,),
    )
    existing = cursor.fetchone()
    if existing:
        return existing[0], existing[1]

    province_id = None
    if province_name:
        cursor.execute("SELECT province_id FROM Provinces WHERE province_name = %s", (province_name,))
        province = cursor.fetchone()
        if province:
            province_id = province[0]

    cursor.execute(
        """
        INSERT INTO Municipalities (municipality_name, province_id)
        VALUES (%s, %s)
        """,
        (municipality_name, province_id),
    )
    return cursor.lastrowid, province_id


def upsert_station(cursor, station, municipality_id: Optional[int], operator_id: int = 3):
    """Avoid duplicate inserts by keying on name+address+operator; update coords if present."""
    station_name = station.get("name")
    address = station.get("address")
    latitude = station.get("latitude")
    longitude = station.get("longitude")

    if not station_name or not address:
        return

    cursor.execute(
        """
        SELECT station_id FROM gas_stations
        WHERE station_name = %s AND address = %s AND operator_id = %s
        """,
        (station_name, address, operator_id),
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE gas_stations
            SET latitude = %s, longitude = %s, municipality_id = %s
            WHERE station_id = %s
            """,
            (latitude, longitude, municipality_id, existing[0]),
        )
    else:
        cursor.execute(
            """
            INSERT INTO gas_stations (station_name, address, latitude, longitude, municipality_id, operator_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (station_name, address, latitude, longitude, municipality_id, operator_id),
        )


def main():
    scraped_data = load_scraped_data("./gas_stations.json")

    db_connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )
    cursor = db_connection.cursor()

    try:
        db_connection.start_transaction()

        for station in scraped_data:
            municipality_name, province_name = parse_city(station.get("city"))
            municipality_id, _ = get_or_create_municipality(cursor, municipality_name, province_name)
            upsert_station(cursor, station, municipality_id)

        db_connection.commit()
    except Exception:
        db_connection.rollback()
        raise
    finally:
        cursor.close()
        db_connection.close()


if __name__ == "__main__":
    main()