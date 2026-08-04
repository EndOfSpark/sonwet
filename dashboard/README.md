# Sonwet dashboard

A read-only Next.js dashboard for exploring the SQLite observations written by the Sonwet collector.

## Local development

The default database path is `../data/weather_data.db`, so development works from this directory without copying the database.

```bash
npm install
npm run dev
```

Open <http://localhost:3000>. Override the database location when needed:

```bash
SQLITE_PATH=/absolute/path/to/weather_data.db npm run dev
```

## One-command Docker launch

From any directory, run:

```bash
./dashboard/run-docker.sh
```

It builds the image, mounts `data/` read-only, and serves the dashboard at
<http://localhost:3000>. The port and data directory can be overridden:

```bash
DASHBOARD_PORT=8080 SONWET_DATA_DIR=/path/to/data ./dashboard/run-docker.sh
```

## Container image

The image is prepared for a later Compose integration but is intentionally not added to the root Compose file yet.

```bash
docker build -t sonwet-dashboard ./dashboard
docker run --rm -p 3000:3000 \
  -v "$(pwd)/data:/data:ro" \
  sonwet-dashboard
```

The container expects the database at `/data/weather_data.db` by default. The bind mount is read-only because the dashboard never writes to the collector database.

Suggested future Compose configuration:

```yaml
dashboard:
  build:
    context: ./dashboard
  environment:
    SQLITE_PATH: /data/weather_data.db
  volumes:
    - ./data:/data:ro
  ports:
    - "3000:3000"
```
