#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_dir="$(cd -- "$script_dir/.." && pwd)"

image_name="${DASHBOARD_IMAGE:-sonwet-dashboard}"
container_name="${DASHBOARD_CONTAINER:-sonwet-dashboard}"
dashboard_port="${DASHBOARD_PORT:-3000}"
data_dir="${SONWET_DATA_DIR:-$repository_dir/data}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required but was not found in PATH." >&2
  exit 1
fi

if [[ ! -f "$data_dir/weather_data.db" ]]; then
  echo "Weather database not found: $data_dir/weather_data.db" >&2
  echo "Set SONWET_DATA_DIR to the directory containing weather_data.db." >&2
  exit 1
fi

if docker container inspect "$container_name" >/dev/null 2>&1; then
  echo "A container named '$container_name' already exists." >&2
  echo "Stop or remove it, or set DASHBOARD_CONTAINER to another name." >&2
  exit 1
fi

echo "Building $image_name..."
docker build --tag "$image_name" "$script_dir"

echo "Starting Sonwet dashboard at http://localhost:$dashboard_port"
echo "Press Ctrl+C to stop it."
docker run --rm \
  --name "$container_name" \
  --init \
  --publish "$dashboard_port:3000" \
  --volume "$data_dir:/data:ro" \
  "$image_name"
