from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

from src.mappings import map_icon_id


GEOSPHERE_BASE = "https://dataset.api.hub.geosphere.at/v1"

INCA_RESOURCE = "inca-v1-1h-1km"
NWP_RESOURCE = "nwp-v1-1h-2500m"

INCA_PARAMS = ["RR", "RH2M", "T2M", "TD2M"]
FORECAST_PARAMS = ["sy"]


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

    Historical INCA fields:
      RR    = 1-hour precipitation sum
      RH2M  = 2m relative humidity
      T2M   = 2m temperature
      TD2M  = 2m dew point temperature

        Forecast field:
            sy    = mapped weather-symbol forecast description

    Drift fields:
      history_drift_minutes:
        selected INCA timestamp minus now.
        Usually negative, because historical data lags behind now.

      forecast_drift_minutes:
        selected forecast valid timestamp minus now.
        Usually positive or zero, because this chooses the next forecast time.

        If flat=True, return only these top-level key/value pairs:
            history_drift_minutes
            forecast_drift_minutes
            RR
            RH2M
            T2M
            TD2M
    """

    if not (-90 <= lat <= 90):
        raise ValueError("lat must be in [-90, 90]")
    if not (-180 <= lon <= 180):
        raise ValueError("lon must be in [-180, 180]")

    now = datetime.now(timezone.utc)

    # Historical INCA: use metadata to avoid requesting beyond available data.
    inca_metadata = _get_json(
        f"/timeseries/historical/{INCA_RESOURCE}/metadata",
        params={},
        timeout=timeout,
    )

    latest_inca_time = _parse_dt(inca_metadata["end_time"])
    history_target = min(now, latest_inca_time)

    history_start = history_target - timedelta(hours=history_hours)
    history_end = history_target

    history_data, history_url = _get_json_with_url(
        f"/timeseries/historical/{INCA_RESOURCE}",
        params={
            "lat_lon": f"{lat},{lon}",
            "parameters": ",".join(INCA_PARAMS),
            "start": _api_dt(history_start),
            "end": _api_dt(history_end),
            "output_format": "geojson",
        },
        timeout=timeout,
    )

    history_idx, history_timestamp = _closest_timestamp(
        history_data,
        target=now,
        prefer_future=False,
    )

    history_point = _nearest_point(history_data)

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

    forecast_symbol = _param_value(forecast_data, "sy", forecast_idx)
    forecast_symbol["value"] = _map_forecast_symbol_value(forecast_symbol["value"])

    result = {
        "requested": {
            "lat": lat,
            "lon": lon,
            "now_utc": now.isoformat(),
        },

        "history": {
            "source": INCA_RESOURCE,
            "timestamp_utc": history_timestamp.isoformat(),
            "history_drift_minutes": _minutes(history_timestamp - now),
            "nearest_grid_point": history_point,
            "url": history_url,
            "fields": {
                param: {
                    **_param_value(history_data, param, history_idx),
                    "timestamp_utc": history_timestamp.isoformat(),
                    "history_drift_minutes": _minutes(history_timestamp - now),
                }
                for param in INCA_PARAMS
            },
        },

        "forecast": {
            "source": NWP_RESOURCE,
            "reference_time_utc": reference_time_dt.isoformat()
            if reference_time_dt
            else None,
            "valid_time_utc": forecast_timestamp.isoformat(),
            "forecast_drift_minutes": _minutes(forecast_timestamp - now),
            "forecast_run_age_minutes": _minutes(now - reference_time_dt)
            if reference_time_dt
            else None,
            "nearest_grid_point": forecast_point,
            "url": forecast_url,
            "fields": {
                "sy": {
                    **forecast_symbol,
                    "valid_time_utc": forecast_timestamp.isoformat(),
                    "forecast_drift_minutes": _minutes(forecast_timestamp - now),
                }
            },
        },
    }

    if flat:
        return _flatten_weather_mapping(result)

    return result


def _flatten_weather_mapping(result: dict[str, Any]) -> dict[str, Any]:
    history_fields = result["history"]["fields"]

    flat_result = {
        "history_drift_minutes": result["history"]["history_drift_minutes"],
        "forecast_drift_minutes": result["forecast"]["forecast_drift_minutes"],
    }

    for param in INCA_PARAMS:
        flat_result[param] = history_fields[param]["value"]

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

    lat = 48.269012
    lon = 14.327416

    print(get_geosphere_weather_mapping(lat, lon))