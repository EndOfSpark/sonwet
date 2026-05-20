from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import signal
from threading import Event

from apscheduler.schedulers.background import BackgroundScheduler

try:
    from .db import initialize_weather_db, insert_weather_sample
    from .weather_api import get_geosphere_weather_mapping
    from .sun_state import sun_angle_and_classification
except ImportError:
    from db import initialize_weather_db, insert_weather_sample
    from weather_api import get_geosphere_weather_mapping
    from sun_state import sun_angle_and_classification


LOGGER = logging.getLogger(__name__)


def collect_weather_sample(lat: float, lon: float, sqlite_path: str) -> int:
    collected_at = datetime.now(timezone.utc)
    weather_data = get_geosphere_weather_mapping(lat, lon, flat=True)
    sun_elevation, sun_state = sun_angle_and_classification(
        lat,
        lon,
        utc_time=collected_at,
    )
    weather_data["sun_elevation"] = sun_elevation
    weather_data["sun_state"] = sun_state
    collected_at_utc = collected_at.isoformat()
    row_id = insert_weather_sample(
        sqlite_path,
        weather_data,
        collected_at_utc=collected_at_utc,
    )

    LOGGER.info(
        "Stored weather sample id=%s collected_at_utc=%s nowcast_timestamp=%s nwp_timestamp=%s sun_elevation=%s sun_state=%s",
        row_id,
        collected_at_utc,
        weather_data["nowcast_timestamp"],
        weather_data["nwp_timestamp"],
        round(weather_data["sun_elevation"], 2),
        weather_data["sun_state"],
    )

    return row_id


def _build_scheduler(
    lat: float,
    lon: float,
    sqlite_path: str,
    job_interval_minutes: int,
) -> BackgroundScheduler:
    if job_interval_minutes < 1:
        raise ValueError("JOB_INTERVAL_MINUTES must be at least 1")

    scheduler = BackgroundScheduler(timezone=timezone.utc)
    scheduler.add_job(
        collect_weather_sample,
        trigger="interval",
        minutes=job_interval_minutes,
        kwargs={
            "lat": lat,
            "lon": lon,
            "sqlite_path": sqlite_path,
        },
        id="weather_collection",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    return scheduler


def _register_shutdown_handlers(stop_event: Event) -> None:
    def _request_stop(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    lat = float(os.environ.get("LATITUDE", "48.20849"))
    lon = float(os.environ.get("LONGITUDE", "16.37208"))
    sqlite_path = os.environ.get("SQLITE_PATH", "weather_data.db")
    job_interval_minutes = int(os.environ.get("JOB_INTERVAL_MINUTES", "10"))

    initialize_weather_db(sqlite_path)
    collect_weather_sample(lat, lon, sqlite_path)

    scheduler = _build_scheduler(lat, lon, sqlite_path, job_interval_minutes)
    scheduler.start()

    stop_event = Event()
    _register_shutdown_handlers(stop_event)

    LOGGER.info(
        "Weather collection scheduler started interval=%s sqlite_path=%s",
        job_interval_minutes,
        sqlite_path,
    )

    try:
        stop_event.wait()
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
