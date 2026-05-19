from __future__ import annotations

from datetime import datetime, timezone
from math import asin, cos, degrees, pi, radians, sin


def sun_angle_and_classification(
    lat: float,
    lon: float,
    utc_time: datetime | str | None = None,
) -> tuple[float, str]:
    """
    Return the sun elevation angle and daylight classification.

    Args:
        lat: Latitude in degrees. North positive.
        lon: Longitude in degrees. East positive.
        utc_time: Optional UTC datetime. If None, uses current UTC time.
                  Naive datetimes are treated as UTC.
                  ISO strings like "2026-05-19T12:00:00Z" are accepted.

    Returns:
        (solar_elevation_degrees, classification)

        classification is one of:
        - "day"
        - "civil_twilight"
        - "nautical_twilight"
        - "astronomical_twilight"
        - "night"
    """

    if not -90.0 <= lat <= 90.0:
        raise ValueError("lat must be between -90 and 90 degrees")

    if not -180.0 <= lon <= 180.0:
        raise ValueError("lon must be between -180 and 180 degrees")

    dt = _parse_utc_time(utc_time)

    day_of_year = dt.timetuple().tm_yday

    fractional_hour = (
        dt.hour
        + dt.minute / 60.0
        + dt.second / 3600.0
        + dt.microsecond / 3_600_000_000.0
    )

    gamma = 2.0 * pi / 365.0 * (day_of_year - 1 + (fractional_hour - 12.0) / 24.0)

    eq_time = 229.18 * (
        0.000075
        + 0.001868 * cos(gamma)
        - 0.032077 * sin(gamma)
        - 0.014615 * cos(2.0 * gamma)
        - 0.040849 * sin(2.0 * gamma)
    )

    decl = (
        0.006918
        - 0.399912 * cos(gamma)
        + 0.070257 * sin(gamma)
        - 0.006758 * cos(2.0 * gamma)
        + 0.000907 * sin(2.0 * gamma)
        - 0.002697 * cos(3.0 * gamma)
        + 0.00148 * sin(3.0 * gamma)
    )

    true_solar_time = (
        fractional_hour * 60.0
        + eq_time
        + 4.0 * lon
    ) % 1440.0

    hour_angle_deg = true_solar_time / 4.0 - 180.0
    if hour_angle_deg < -180.0:
        hour_angle_deg += 360.0

    lat_rad = radians(lat)
    hour_angle_rad = radians(hour_angle_deg)

    elevation_rad = asin(
        sin(lat_rad) * sin(decl)
        + cos(lat_rad) * cos(decl) * cos(hour_angle_rad)
    )

    elevation_deg = degrees(elevation_rad)

    classification = _classify_sun_elevation(elevation_deg)

    return elevation_deg, classification


def _parse_utc_time(utc_time: datetime | str | None) -> datetime:
    if utc_time is None:
        return datetime.now(timezone.utc)

    if isinstance(utc_time, str):
        value = utc_time.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
    elif isinstance(utc_time, datetime):
        dt = utc_time
    else:
        raise TypeError("utc_time must be datetime, ISO string, or None")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def _classify_sun_elevation(elevation_deg: float) -> str:
    if elevation_deg >= -0.833:
        return "day"

    if elevation_deg >= -6.0:
        return "civil_twilight"

    if elevation_deg >= -12.0:
        return "nautical_twilight"

    if elevation_deg >= -18.0:
        return "astronomical_twilight"

    return "night"


if __name__ == "__main__":
    import os
    angle, classification = sun_angle_and_classification(
        lat=float(os.environ.get("LATITUDE", "48.269012")),
        lon=float(os.environ.get("LONGITUDE", "14.3382225"))
    )

    print((round(angle, 2), classification))