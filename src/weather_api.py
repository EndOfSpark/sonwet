from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

try:
    from .globals import map_icon_id
except ImportError:
    from globals import map_icon_id


GEOSPHERE_BASE = "https://dataset.api.hub.geosphere.at/v1"

NOWCAST_RESOURCE = "nowcast-v1-15min-1km"
NWP_RESOURCE = "nwp-v1-1h-2500m"

NOWCAST_PARAMS = {
    "RR": "rr",
    "RH2M": "rh2m",
    "T2M": "t2m",
}
FORECAST_PARAMS = ["sy"]

def classify_rain(value_kg_m2: float, interval_minutes: int = 60) -> str:
    """
    Classify liquid precipitation intensity.

    value_kg_m2:
        Accumulated precipitation over the interval.
        For liquid water: kg/m² == mm.

    interval_minutes:
        Measurement/forecast accumulation interval.
        Use 15 for GeoSphere nowcast-v1-15min-1km.
        Use 10 for 10-minute station data.
    """

    if value_kg_m2 is None:
        return "unknown"

    if value_kg_m2 < 0:
        return "unknown"

    rate = value_kg_m2 * 60.0 / interval_minutes

    if rate < 0.1:
        return "none"

    if rate < 0.5:
        return "trace"

    if rate < 2.5:
        return "light"

    if rate < 10.0:
        return "moderate"

    if rate < 50.0:
        return "heavy"

    return "violent"

def get_geosphere_weather_mapping(
    lat: float,
    lon: float,
    *,
    history_hours: int = 12,
    forecast_hours: int = 6,
    timeout: int = 20,
    flat: bool = False,
) -> dict[str, Any]:
    """
    Return a simple key/value mapping for one coordinate.

        Nowcast fields:
            RR    = 15-minute precipitation sum in kg m-2 (mm)
            RH2M  = 2m relative humidity in %
            T2M   = 2m temperature in degrees Celsius

        Forecast field:
            sy    = mapped weather-symbol forecast description

    Drift fields:
            nowcast_drift_minutes:
                selected nowcast timestamp minus now.
                Usually near zero because this chooses the nearest nowcast time.

            nwp_drift_minutes:
                selected NWP valid timestamp minus now.
        Usually positive or zero, because this chooses the next forecast time.

        If flat=True, return only these top-level key/value pairs:
            nowcast_timestamp
            nwp_timestamp
            nowcast_drift_minutes
            nwp_drift_minutes
            RR
            rain_classification
            RH2M
            T2M
            sy
    """

    if not (-90 <= lat <= 90):
        raise ValueError("lat must be in [-90, 90]")
    if not (-180 <= lon <= 180):
        raise ValueError("lon must be in [-180, 180]")

    now = datetime.now(timezone.utc)

    # GeoSphere nowcast is exposed as a forecast endpoint and returns a rolling
    # short-range horizon for the selected coordinate.
    nowcast_data, nowcast_url = _get_json_with_url(
        f"/timeseries/forecast/{NOWCAST_RESOURCE}",
        params={
            "lat_lon": f"{lat},{lon}",
            "parameters": ",".join(NOWCAST_PARAMS.values()),
            "forecast_offset": "0",
            "output_format": "geojson",
        },
        timeout=timeout,
    )

    nowcast_idx, nowcast_timestamp = _closest_timestamp(
        nowcast_data,
        target=now,
        prefer_future=False,
    )

    nowcast_point = _nearest_point(nowcast_data)

    # Forecast: choose the next valid sy timestamp closest to now.
    forecast_start = now
    forecast_end = now + timedelta(hours=forecast_hours)

    forecast_data, forecast_url = _get_json_with_url(
        f"/timeseries/forecast/{NWP_RESOURCE}",
        params={
            "lat_lon": f"{lat},{lon}",
            "parameters": ",".join(FORECAST_PARAMS),
            "forecast_offset": "0",
            "start": _api_dt(forecast_start),
            "end": _api_dt(forecast_end),
            "output_format": "geojson",
        },
        timeout=timeout,
    )

    forecast_idx, forecast_timestamp = _closest_timestamp(
        forecast_data,
        target=now,
        prefer_future=True,
    )

    forecast_point = _nearest_point(forecast_data)

    reference_time = forecast_data.get("reference_time")
    reference_time_dt = _parse_dt(reference_time) if reference_time else None

    history_fields = {
        output_param: {
            **_param_value(nowcast_data, query_param, nowcast_idx),
            "timestamp_utc": nowcast_timestamp.isoformat(),
            "nowcast_drift_minutes": _minutes(nowcast_timestamp - now),
        }
        for output_param, query_param in NOWCAST_PARAMS.items()
    }
    history_fields["RR"]["rain_classification"] = classify_rain(
        history_fields["RR"]["value"],
        interval_minutes=15,
    )

    forecast_symbol = _param_value(forecast_data, "sy", forecast_idx)
    forecast_symbol["value"] = _map_forecast_symbol_value(forecast_symbol["value"])

    result = {
        "requested": {
            "lat": lat,
            "lon": lon,
            "now_utc": now.isoformat(),
        },

        "history": {
            "source": NOWCAST_RESOURCE,
            "timestamp_utc": nowcast_timestamp.isoformat(),
            "nowcast_drift_minutes": _minutes(nowcast_timestamp - now),
            "nearest_grid_point": nowcast_point,
            "url": nowcast_url,
            "fields": history_fields,
        },

        "forecast": {
            "source": NWP_RESOURCE,
            "reference_time_utc": reference_time_dt.isoformat()
            if reference_time_dt
            else None,
            "valid_time_utc": forecast_timestamp.isoformat(),
            "nwp_drift_minutes": _minutes(forecast_timestamp - now),
            "forecast_run_age_minutes": _minutes(now - reference_time_dt)
            if reference_time_dt
            else None,
            "nearest_grid_point": forecast_point,
            "url": forecast_url,
            "fields": {
                "sy": {
                    **forecast_symbol,
                    "valid_time_utc": forecast_timestamp.isoformat(),
                    "nwp_drift_minutes": _minutes(forecast_timestamp - now),
                }
            },
        },
    }

    if flat:
        return _flatten_weather_mapping(result)

    return result


def _flatten_weather_mapping(result: dict[str, Any]) -> dict[str, Any]:
    history_fields = result["history"]["fields"]
    forecast_fields = result["forecast"]["fields"]

    flat_result = {
        "nowcast_timestamp": result["history"]["timestamp_utc"],
        "nwp_timestamp": result["forecast"]["valid_time_utc"],
        "nowcast_drift_minutes": result["history"]["nowcast_drift_minutes"],
        "nwp_drift_minutes": result["forecast"]["nwp_drift_minutes"],
        "sy": forecast_fields["sy"]["value"],
    }

    for param in NOWCAST_PARAMS:
        flat_result[param] = history_fields[param]["value"]

    flat_result["rain_classification"] = history_fields["RR"]["rain_classification"]

    return flat_result


def _map_forecast_symbol_value(value: Any) -> str | None:
    if isinstance(value, int):
        return map_icon_id(value)

    if isinstance(value, float) and value.is_integer():
        return map_icon_id(int(value))

    return None


def _get_json(path: str, *, params: dict[str, str], timeout: int) -> dict[str, Any]:
    url = f"{GEOSPHERE_BASE}{path}"
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _get_json_with_url(
    path: str,
    *,
    params: dict[str, str],
    timeout: int,
) -> tuple[dict[str, Any], str]:
    url = f"{GEOSPHERE_BASE}{path}"
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json(), r.url


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _api_dt(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def _minutes(delta) -> float:
    return round(delta.total_seconds() / 60.0, 1)


def _closest_timestamp(
    data: dict[str, Any],
    *,
    target: datetime,
    prefer_future: bool,
) -> tuple[int, datetime]:
    timestamps = [_parse_dt(t) for t in data["timestamps"]]

    if prefer_future:
        future = [
            (idx, ts)
            for idx, ts in enumerate(timestamps)
            if ts >= target
        ]
        if future:
            return min(future, key=lambda x: x[1] - target)

    return min(
        enumerate(timestamps),
        key=lambda x: abs((x[1] - target).total_seconds()),
    )


def _nearest_point(data: dict[str, Any]) -> dict[str, float]:
    feature = data["features"][0]
    lon, lat = feature["geometry"]["coordinates"]
    return {
        "lat": lat,
        "lon": lon,
    }


def _param_value(
    data: dict[str, Any],
    param: str,
    idx: int,
) -> dict[str, Any]:
    parameters = data["features"][0]["properties"]["parameters"]

    key = None
    for candidate in parameters:
        if candidate.lower() == param.lower():
            key = candidate
            break

    if key is None:
        raise KeyError(f"Parameter {param!r} not found. Available: {list(parameters)}")

    payload = parameters[key]
    values = payload.get("data", [])

    return {
        "value": values[idx] if idx < len(values) else None,
        "unit": payload.get("unit"),
        "name": payload.get("name", key),
    }

if __name__ == "__main__":
    import os
    lat = float(os.environ.get("LATITUDE", "48.20849"))
    lon = float(os.environ.get("LONGITUDE", "16.37208"))

    print(get_geosphere_weather_mapping(lat, lon, flat=True))