import Database from "better-sqlite3";
import path from "node:path";

export const periods = {
  "24h": { label: "24 hours", hours: 24 },
  "7d": { label: "7 days", hours: 24 * 7 },
  "30d": { label: "30 days", hours: 24 * 30 },
  all: { label: "All time", hours: null },
} as const;

export type Period = keyof typeof periods;

export type WeatherRow = {
  id: number;
  collected_at_utc: string;
  nowcast_drift_minutes: number;
  nwp_drift_minutes: number;
  sy: string | null;
  RR: number | null;
  RH2M: number | null;
  T2M: number | null;
  rain_classification: string;
  sun_elevation: number;
  sun_state: string;
};

export type ChartPoint = {
  timestamp: string;
  temperature: number | null;
  humidity: number | null;
  rain: number;
  sunElevation: number;
  sunState: string;
  condition: string;
  conditionBand: number;
};

export type DashboardData = {
  databasePath: string;
  latestAt: string;
  firstAt: string;
  rangeStart: string;
  rangeEnd: string;
  sampleCount: number;
  current: WeatherRow;
  stats: { avgTemp: number | null; minTemp: number | null; maxTemp: number | null; avgHumidity: number | null; totalRain: number; wetSamples: number };
  chart: ChartPoint[];
  observations: WeatherRow[];
  avgNowcastDrift: number;
  avgNwpDrift: number;
};

export type DateRange = { from?: string; to?: string };

function openDatabase() {
  const databasePath = path.resolve(/* turbopackIgnore: true */ process.env.SQLITE_PATH || path.join(process.cwd(), "..", "data", "weather_data.db"));
  const database = new Database(databasePath, { readonly: true, fileMustExist: true });
  database.pragma("query_only = ON");
  return { database, databasePath };
}

export function getDashboardData(period: Period, range: DateRange = {}): DashboardData {
  const { database, databasePath } = openDatabase();
  try {
    const bounds = database.prepare(`SELECT MIN(collected_at_utc) firstAt, MAX(collected_at_utc) latestAt FROM weather_samples`).get() as { firstAt: string; latestAt: string };
    if (!bounds.latestAt) throw new Error("The weather database contains no observations yet.");

    const hours = periods[period].hours;
    const quickRangeStart = hours === null ? bounds.firstAt : new Date(new Date(bounds.latestAt).getTime() - hours * 3_600_000).toISOString();
    const customRange = Boolean(range.from || range.to);
    let from = range.from ? new Date(`${range.from}T00:00:00.000Z`).toISOString() : customRange ? bounds.firstAt : quickRangeStart;
    let to = range.to ? new Date(`${range.to}T23:59:59.999Z`).toISOString() : bounds.latestAt;
    if (from > to) [from, to] = [to, from];
    const rows = database.prepare(`
      SELECT id, collected_at_utc, nowcast_drift_minutes, nwp_drift_minutes, sy, RR, RH2M, T2M,
             rain_classification, sun_elevation, sun_state
      FROM weather_samples WHERE collected_at_utc >= ? AND collected_at_utc <= ? ORDER BY collected_at_utc ASC
    `).all(from, to) as WeatherRow[];

    if (!rows.length) throw new Error("No observations were found in this time window.");

    const numeric = (values: (number | null)[]) => values.filter((value): value is number => value !== null);
    const temperatures = numeric(rows.map((row) => row.T2M));
    const humidities = numeric(rows.map((row) => row.RH2M));
    const mean = (values: number[]) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
    const dominant = (values: (string | null)[]) => {
      const counts = new Map<string, number>();
      for (const value of values) {
        const name = value ?? "unknown";
        counts.set(name, (counts.get(name) ?? 0) + 1);
      }
      return [...counts].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "unknown";
    };

    // Preserve enough temporal detail for the daily solar curve. The previous
    // 180-point cap aliased sunrise/sunset heavily on longer ranges.
    const targetPoints = 1_440;
    const bucketSize = Math.max(1, Math.ceil(rows.length / targetPoints));
    const chart: ChartPoint[] = [];
    for (let index = 0; index < rows.length; index += bucketSize) {
      const bucket = rows.slice(index, index + bucketSize);
      const last = bucket.at(-1)!;
      chart.push({
        timestamp: last.collected_at_utc,
        temperature: mean(numeric(bucket.map((row) => row.T2M))),
        humidity: mean(numeric(bucket.map((row) => row.RH2M))),
        rain: bucket.reduce((sum, row) => sum + (row.RR ?? 0), 0),
        sunElevation: mean(bucket.map((row) => row.sun_elevation)) ?? 0,
        sunState: dominant(bucket.map((row) => row.sun_state)),
        condition: dominant(bucket.map((row) => row.sy)),
        conditionBand: 1,
      });
    }

    const current = rows.at(-1)!;
    return {
      databasePath,
      latestAt: bounds.latestAt,
      firstAt: bounds.firstAt,
      rangeStart: rows[0].collected_at_utc,
      rangeEnd: rows.at(-1)!.collected_at_utc,
      sampleCount: rows.length,
      current,
      stats: {
        avgTemp: mean(temperatures),
        minTemp: temperatures.length ? Math.min(...temperatures) : null,
        maxTemp: temperatures.length ? Math.max(...temperatures) : null,
        avgHumidity: mean(humidities),
        totalRain: rows.reduce((sum, row) => sum + (row.RR ?? 0), 0),
        wetSamples: rows.filter((row) => (row.RR ?? 0) > 0).length,
      },
      chart,
      observations: rows.slice(-24).reverse(),
      avgNowcastDrift: mean(rows.map((row) => Math.abs(row.nowcast_drift_minutes))) ?? 0,
      avgNwpDrift: mean(rows.map((row) => Math.abs(row.nwp_drift_minutes))) ?? 0,
    };
  } finally {
    database.close();
  }
}
