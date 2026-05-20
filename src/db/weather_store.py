from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


WEATHER_SAMPLE_COLUMNS = {
    "id",
    "collected_at_utc",
    "nowcast_timestamp",
    "nwp_timestamp",
    "nowcast_drift_minutes",
    "nwp_drift_minutes",
    "sy",
    "RR",
    "RH2M",
    "T2M",
    "rain_classification",
    "sun_elevation",
    "sun_state",
}


def initialize_weather_db(sqlite_path: str) -> None:
    db_path = Path(sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collected_at_utc TEXT NOT NULL,
                nowcast_timestamp TEXT NOT NULL,
                nwp_timestamp TEXT NOT NULL,
                nowcast_drift_minutes REAL NOT NULL,
                nwp_drift_minutes REAL NOT NULL,
                sy TEXT,
                "RR" REAL,
                "RH2M" REAL,
                "T2M" REAL,
                rain_classification TEXT NOT NULL,
                sun_elevation REAL NOT NULL,
                sun_state TEXT NOT NULL
            )
            """
        )
        existing_columns = _get_table_columns(connection, "weather_samples")
        missing_columns = WEATHER_SAMPLE_COLUMNS.difference(existing_columns)
        if missing_columns:
            missing_list = ", ".join(sorted(missing_columns))
            raise RuntimeError(
                f"Database schema at {db_path} is missing columns: {missing_list}. "
                "Delete the existing database file to recreate it; automatic migration is not implemented."
            )
        connection.commit()


def insert_weather_sample(
    sqlite_path: str,
    weather_data: Mapping[str, Any],
    collected_at_utc: str | None = None,
) -> int:
    inserted_at = collected_at_utc or datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(sqlite_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO weather_samples (
                collected_at_utc,
                nowcast_timestamp,
                nwp_timestamp,
                nowcast_drift_minutes,
                nwp_drift_minutes,
                sy,
                "RR",
                "RH2M",
                "T2M",
                rain_classification,
                sun_elevation,
                sun_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inserted_at,
                weather_data["nowcast_timestamp"],
                weather_data["nwp_timestamp"],
                weather_data["nowcast_drift_minutes"],
                weather_data["nwp_drift_minutes"],
                weather_data["sy"],
                weather_data["RR"],
                weather_data["RH2M"],
                weather_data["T2M"],
                weather_data["rain_classification"],
                weather_data["sun_elevation"],
                weather_data["sun_state"],
            ),
        )
        connection.commit()

    return int(cursor.lastrowid)


def _get_table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return {row[1] for row in rows}