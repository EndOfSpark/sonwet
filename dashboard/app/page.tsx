import { Activity, CloudRain, Database, Droplets, Gauge, RefreshCw, Sunrise, Thermometer, Waves } from "lucide-react";
import Link from "next/link";
import { WeatherTimelineSuite } from "@/components/charts";
import { getDashboardData, periods, type Period } from "@/lib/weather";

export const dynamic = "force-dynamic";

const number = (value: number | null, digits = 1) => value === null ? "—" : value.toFixed(digits);
const words = (value: string | null) => (value ?? "unknown").replaceAll("_", " ");
const dateTime = (value: string) => new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value));

const validDate = (value?: string) => {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return undefined;
  return Number.isNaN(new Date(`${value}T00:00:00.000Z`).getTime()) ? undefined : value;
};

export default async function Dashboard({ searchParams }: { searchParams: Promise<{ period?: string; from?: string; to?: string }> }) {
  const query = await searchParams;
  const period: Period = query.period && query.period in periods ? query.period as Period : "7d";
  const from = validDate(query.from);
  const to = validDate(query.to);
  const data = getDashboardData(period, { from, to });
  const latest = data.current;

  return <main>
    <header className="topbar portal-topbar">
      <div className="brand"><div className="brandmark"><Waves size={22}/></div><div><b>SONWET</b><span>WEATHER ARCHIVE</span></div></div>
      <div className="portal-nav"><span>OBSERVATIONS</span><span>UTC</span><span>SQLite</span></div>
      <div className="status"><i/> UPDATED {dateTime(data.latestAt)} UTC</div>
    </header>

    <div className="page-shell">
      <section className="hero">
        <div><p className="eyebrow"><Activity size={14}/> WEATHER DATA</p><h1>Observation archive</h1></div>
        <span className="archive-meta">RECORDS {data.sampleCount.toLocaleString()}　|　FROM {dateTime(data.rangeStart)}　|　TO {dateTime(data.rangeEnd)}</span>
      </section>

      <section className="range-toolbar">
        <div className="toolbar-label">PERIOD<br/><small>DATE RANGE</small></div>
        <nav className="period-picker" aria-label="Quick time ranges">{Object.entries(periods).map(([key, config]) => <Link className={!from && !to && period === key ? "active" : ""} key={key} href={`/?period=${key}`}>{config.label}</Link>)}</nav>
        <form className="date-form" method="get">
          <label>FROM<input type="date" name="from" defaultValue={from ?? data.rangeStart.slice(0, 10)} min={data.firstAt.slice(0, 10)} max={data.latestAt.slice(0, 10)}/></label>
          <span>→</span>
          <label>TO<input type="date" name="to" defaultValue={to ?? data.rangeEnd.slice(0, 10)} min={data.firstAt.slice(0, 10)} max={data.latestAt.slice(0, 10)}/></label>
          <button type="submit">APPLY</button>
          {(from || to) && <Link href="/?period=7d">RESET</Link>}
        </form>
      </section>

      <section className="now-card">
        <div className="now-main"><span className="weather-orb">{(latest.RR ?? 0) > 0 ? <CloudRain/> : <Sunrise/>}</span><div><p>Latest observation</p><strong>{number(latest.T2M)}<sup>°C</sup></strong><span>{words(latest.sy)} · {words(latest.sun_state)}</span></div></div>
        <div className="now-detail"><Droplets/><span>Humidity<b>{number(latest.RH2M)}%</b></span></div>
        <div className="now-detail"><CloudRain/><span>Rain / 15 min<b>{number(latest.RR, 2)} mm</b></span></div>
        <div className="now-detail"><Sunrise/><span>Sun elevation<b>{number(latest.sun_elevation)}°</b></span></div>
        <div className="now-detail"><RefreshCw/><span>NWP lead<b>{number(latest.nwp_drift_minutes)} min</b></span></div>
      </section>

      <section className="metric-grid">
        <article className="metric"><span><Thermometer/> AVG TEMPERATURE</span><strong>{number(data.stats.avgTemp)}<small>°C</small></strong><p><b>{number(data.stats.minTemp)}°</b> low <em/> <b>{number(data.stats.maxTemp)}°</b> high</p></article>
        <article className="metric"><span><Droplets/> AVG HUMIDITY</span><strong>{number(data.stats.avgHumidity)}<small>%</small></strong><p>Across {data.sampleCount.toLocaleString()} readings</p></article>
        <article className="metric"><span><CloudRain/> ACCUMULATED RAIN</span><strong>{number(data.stats.totalRain, 2)}<small>mm</small></strong><p>{data.stats.wetSamples.toLocaleString()} wet readings</p></article>
        <article className="metric"><span><Gauge/> SOURCE ALIGNMENT</span><strong>±{number(data.avgNowcastDrift)}<small>min</small></strong><p>Forecast mean drift ±{number(data.avgNwpDrift)} min</p></article>
      </section>

      <WeatherTimelineSuite data={data.chart}/>

      <section className="panel table-panel"><div className="panel-head"><div><p>RAW OBSERVATIONS</p><h2>Recent readings</h2></div><span className="sample-chip"><Database size={13}/>{data.sampleCount.toLocaleString()} in range</span></div><div className="table-scroll"><table><thead><tr><th>Collected (UTC)</th><th>Condition</th><th>Temperature</th><th>Humidity</th><th>Rain</th><th>Intensity</th><th>Sun</th><th>Drift</th></tr></thead><tbody>{data.observations.map(row => <tr key={row.id}><td className="mono">{dateTime(row.collected_at_utc)}</td><td>{words(row.sy)}</td><td>{number(row.T2M)} °C</td><td>{number(row.RH2M)}%</td><td>{number(row.RR, 2)} mm</td><td><span className={`pill rain-${row.rain_classification}`}>{words(row.rain_classification)}</span></td><td>{words(row.sun_state)}</td><td className="mono">{number(row.nowcast_drift_minutes)}m</td></tr>)}</tbody></table></div></section>

      <footer><span>Coverage: {dateTime(data.firstAt)} — {dateTime(data.latestAt)} UTC</span><span>SQLite · read only · {data.sampleCount.toLocaleString()} visible samples</span></footer>
    </div>
  </main>;
}
