try:
    from .weather_api import get_geosphere_weather_mapping
    from .sun_state import sun_angle_and_classification
except ImportError:
    from weather_api import get_geosphere_weather_mapping
    from sun_state import sun_angle_and_classification

import os

def main():
    lat = float(os.environ.get("LATITUDE", "48.269012"))
    lon = float(os.environ.get("LONGITUDE", "14.327416"))
    sqlite_path = os.environ.get("SQLITE_PATH", "weather_data.db")
    job_interval_minutes = int(os.environ.get("JOB_INTERVAL_MINUTES", "10"))


if __name__ == "__main__":
    main()
