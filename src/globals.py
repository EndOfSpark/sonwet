GEOSPHERE_ATTRIBUTION = {
    "source": "GeoSphere Austria",
    "source_url": "https://data.hub.geosphere.at",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": "Datenquelle: GeoSphere Austria - https://data.hub.geosphere.at",
}

ICON_ID_TO_DESCRIPTION = {
    1: "cloudless",
    2: "clear",
    3: "cloudy",
    4: "heavily_cloudy",
    5: "overcast",
    6: "ground_fog",
    7: "high_fog",
    8: "light_rain",
    9: "moderate_rain",
    10: "strong_rain",
    11: "sleet",
    12: "sleet",
    13: "sleet",
    14: "light_snowfall",
    15: "moderate_snowfall",
    16: "strong_snowfall",
    17: "rain_shower",
    18: "rain_shower",
    19: "strong_rain_shower",
    20: "sleet_shower",
    21: "sleet_shower",
    22: "sleet_shower",
    23: "snow_shower",
    24: "snow_shower",
    25: "strong_snow_shower",
    26: "thunderstorm",
    27: "thunderstorm",
    28: "strong_thunderstorm",
    29: "thunderstorm_with_sleet",
    30: "strong_thunderstorm_with_sleet",
    31: "thunderstorm_with_snow",
    32: "strong_thunderstorm_with_snow",
}


def map_icon_id(icon_id: int) -> str | None:
    return ICON_ID_TO_DESCRIPTION.get(icon_id)