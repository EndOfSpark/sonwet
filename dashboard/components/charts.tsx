"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Area, Bar, Brush, CartesianGrid, Cell, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ChartPoint } from "@/lib/weather";

const SUN_COLORS: Record<string, string> = {
  day: "#d88b16",
  civil_twilight: "#c4512b",
  nautical_twilight: "#58658f",
  astronomical_twilight: "#303b63",
  night: "#151c35",
};

const CONDITION_COLORS: Record<string, string> = {
  cloudless: "#d99518", clear: "#edb64b", cloudy: "#7c91a1", heavily_cloudy: "#536777",
  overcast: "#3f4e59", light_rain: "#4d8cac", moderate_rain: "#316887", strong_rain: "#24516f",
  rain_shower: "#3483a1", thunderstorm: "#674f84", strong_thunderstorm: "#513665", unknown: "#85827a",
};

const tooltipStyle = { background: "#17211f", border: "1px solid #344743", borderRadius: 0, color: "#f3f6ee", fontSize: 12 };
const axisTick = { fill: "#4b4a46", fontSize: 11 };
const words = (value: string) => value.replaceAll("_", " ");
const shortDate = (value: string) => new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));

function ChartHeader({ eyebrow, title, detail }: { eyebrow: string; title: string; detail?: string }) {
  return <div className="panel-head"><div><p>{eyebrow}</p><h2>{title}</h2></div>{detail && <span className="chart-instruction">{detail}</span>}</div>;
}

export function WeatherTimelineSuite({ data }: { data: ChartPoint[] }) {
  const [series, setSeries] = useState({ temperature: true, humidity: true, rain: true });
  const [selection, setSelection] = useState({ startIndex: 0, endIndex: Math.max(0, data.length - 1) });
  const [brushVersion, setBrushVersion] = useState(0);
  const [drag, setDrag] = useState<{ start: string | null; end: string | null }>({ start: null, end: null });
  const brushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const visibleData = useMemo(() => data.slice(selection.startIndex, selection.endIndex + 1), [data, selection.startIndex, selection.endIndex]);
  const selectedStart = data[selection.startIndex]?.timestamp;
  const selectedEnd = data[selection.endIndex]?.timestamp;
  const sunDomain = useMemo<[number, number]>(() => {
    const sunValues = visibleData.map((point) => point.sunElevation);
    const minimum = Math.min(...sunValues);
    const maximum = Math.max(...sunValues);
    const padding = Math.max(5, (maximum - minimum) * 0.08);
    return [Math.floor(minimum - padding), Math.ceil(maximum + padding)];
  }, [visibleData]);
  const sunGradientStops = useMemo(() => visibleData.map((point, index) => <stop key={point.timestamp} offset={`${visibleData.length <= 1 ? 0 : index / (visibleData.length - 1) * 100}%`} stopColor={SUN_COLORS[point.sunState] ?? "#777"}/>), [visibleData]);

  const toggle = (key: keyof typeof series) => setSeries((current) => {
    if (current[key] && Object.values(current).filter(Boolean).length === 1) return current;
    return { ...current, [key]: !current[key] };
  });
  useEffect(() => () => { if (brushTimer.current) clearTimeout(brushTimer.current); }, []);
  const applySelection = (next: { startIndex: number; endIndex: number }) => {
    setSelection(next);
    setBrushVersion((version) => version + 1);
  };
  const queueBrushSelection = (next: { startIndex: number; endIndex: number }) => {
    if (brushTimer.current) clearTimeout(brushTimer.current);
    brushTimer.current = setTimeout(() => setSelection(next), 140);
  };
  const resetZoom = () => applySelection({ startIndex: 0, endIndex: Math.max(0, data.length - 1) });
  const activeTimestamp = (state: unknown) => {
    if (!state || typeof state !== "object" || !("activeLabel" in state)) return null;
    const value = (state as { activeLabel?: unknown }).activeLabel;
    return typeof value === "string" ? value : null;
  };
  const finishDrag = () => {
    if (drag.start && drag.end && drag.start !== drag.end) {
      const start = data.findIndex((point) => point.timestamp === drag.start);
      const end = data.findIndex((point) => point.timestamp === drag.end);
      if (start >= 0 && end >= 0) applySelection({ startIndex: Math.min(start, end), endIndex: Math.max(start, end) });
    }
    setDrag({ start: null, end: null });
  };

  const conditions = useMemo(() => [...new Set(visibleData.map((point) => point.condition))], [visibleData]);

  return <>
    <section className="panel wide timeline-panel">
      <ChartHeader eyebrow="WEATHER HISTORY" title="Temperature, humidity and rainfall" detail="DRAG ACROSS THE PLOT OR USE THE HANDLES TO ZOOM"/>
      <div className="chart-large weather-chart">
        <div className="chart-controls" aria-label="Visible chart series">
          <div className="series-toggles">
            <button type="button" className="temperature" aria-pressed={series.temperature} onClick={() => toggle("temperature")}>Temperature</button>
            <button type="button" className="humidity" aria-pressed={series.humidity} onClick={() => toggle("humidity")}>Humidity</button>
            <button type="button" className="rainfall" aria-pressed={series.rain} onClick={() => toggle("rain")}>Rainfall</button>
          </div>
          <div className="zoom-status"><span>{selectedStart && selectedEnd ? `${shortDate(selectedStart)} — ${shortDate(selectedEnd)}` : ""}</span><button type="button" onClick={resetZoom} disabled={selection.startIndex === 0 && selection.endIndex === data.length - 1}>RESET ZOOM</button></div>
        </div>
        <div className="weather-plot"><ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 0, bottom: 0, left: 0 }}
            onMouseDown={(state) => { const timestamp = activeTimestamp(state); if (timestamp) setDrag({ start: timestamp, end: timestamp }); }}
            onMouseMove={(state) => { const timestamp = activeTimestamp(state); if (drag.start && timestamp) setDrag((current) => ({ ...current, end: timestamp })); }}
            onMouseUp={finishDrag} onMouseLeave={() => drag.start && finishDrag()}>
            <defs><linearGradient id="temperature" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#a61f28" stopOpacity={0.24}/><stop offset="1" stopColor="#a61f28" stopOpacity={0.02}/></linearGradient></defs>
            <CartesianGrid stroke="#d3d0c7" strokeDasharray="3 4" vertical={false}/>
            <XAxis dataKey="timestamp" tickFormatter={shortDate} minTickGap={54} axisLine={false} tickLine={false} tick={axisTick}/>
            <YAxis width={58} yAxisId="temp" orientation="left" hide={!series.temperature} axisLine={false} tickLine={false} tick={axisTick} tickFormatter={(value) => `${Number(value).toFixed(0)}°`} label={{ value: "°C", angle: -90, position: "insideLeft", fill: "#4b4a46", fontSize: 10 }} domain={["auto", "auto"]}/>
            <YAxis width={50} yAxisId="humidity" hide={!series.humidity} orientation="right" axisLine={false} tickLine={false} tick={axisTick} unit="%" domain={[0, 100]}/>
            <YAxis width={0} yAxisId="rain" hide domain={[0, "auto"]}/>
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(value) => shortDate(String(value))} formatter={(value, name) => [`${Number(value).toFixed(name === "Rainfall" ? 2 : 1)}${name === "Humidity" ? "%" : name === "Rainfall" ? " mm" : "°C"}`, name]}/>
            {series.rain && <Bar isAnimationActive={false} yAxisId="rain" dataKey="rain" name="Rainfall" fill="#2f6597" fillOpacity={0.58} maxBarSize={14}/>}
            {series.temperature && <Area isAnimationActive={false} yAxisId="temp" dataKey="temperature" name="Temperature" type="linear" stroke="#a61f28" strokeWidth={2.6} fill="url(#temperature)" dot={false}/>}
            {series.humidity && <Line isAnimationActive={false} yAxisId="humidity" dataKey="humidity" name="Humidity" type="linear" stroke="#126878" strokeWidth={2.1} strokeDasharray="6 4" dot={false}/>}
            {drag.start && drag.end && <ReferenceArea yAxisId="temp" x1={drag.start} x2={drag.end} fill="#d7a72d" fillOpacity={0.24} stroke="#9a7414"/>}
            <Brush key={brushVersion} dataKey="timestamp" height={26} travellerWidth={8} startIndex={selection.startIndex} endIndex={selection.endIndex} tickFormatter={shortDate} stroke="#243f5c" fill="#e2e0d8" onChange={(range) => queueBrushSelection({ startIndex: range.startIndex ?? 0, endIndex: range.endIndex ?? data.length - 1 })}/>
          </ComposedChart>
        </ResponsiveContainer></div>
      </div>
    </section>

    <section className="panel wide timeline-panel">
      <ChartHeader eyebrow="SOLAR POSITION" title="Sun elevation by daylight state" detail="SYNCHRONIZED WITH THE SELECTED WEATHER RANGE"/>
      <div className="chart-large synchronized-chart"><ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={visibleData} margin={{ top: 12, right: 50, bottom: 8, left: 8 }}>
          <defs><linearGradient id="sun-state-line" x1="0" y1="0" x2="1" y2="0">{sunGradientStops}</linearGradient></defs>
          <CartesianGrid stroke="#d3d0c7" strokeDasharray="3 4" vertical={false}/>
          <XAxis dataKey="timestamp" tickFormatter={shortDate} minTickGap={54} axisLine={false} tickLine={false} tick={axisTick}/>
          <YAxis width={50} axisLine={false} tickLine={false} tick={axisTick} unit="°" domain={sunDomain} allowDataOverflow={false}/>
          <ReferenceLine y={0} stroke="#7d776c" strokeDasharray="4 3" label={{ value: "HORIZON", fill: "#6a665f", fontSize: 9 }}/>
          <Tooltip contentStyle={tooltipStyle} labelFormatter={(value) => shortDate(String(value))} formatter={(value, name, item) => name === "Sun elevation" ? [`${Number(value).toFixed(1)}° · ${words(String(item.payload.sunState))}`, name] : [value, name]}/>
          <Line isAnimationActive={false} dataKey="sunElevation" name="Sun elevation" type="linear" stroke="url(#sun-state-line)" strokeWidth={2.2} dot={false}/>
        </ComposedChart>
      </ResponsiveContainer></div>
      <div className="state-legend">{Object.entries(SUN_COLORS).map(([name, color]) => <span key={name}><i style={{ background: color }}/>{words(name)}</span>)}</div>
    </section>

    <section className="panel wide condition-panel">
      <ChartHeader eyebrow="FORECAST CONDITIONS" title="Dominant condition over time" detail="SAME SELECTED UTC WINDOW"/>
      <div className="condition-chart"><ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={visibleData} margin={{ top: 8, right: 50, bottom: 4, left: 8 }}>
          <XAxis dataKey="timestamp" tickFormatter={shortDate} minTickGap={54} axisLine={false} tickLine={false} tick={axisTick}/>
          <YAxis width={50} hide domain={[0, 1]}/>
          <Tooltip contentStyle={tooltipStyle} labelFormatter={(value) => shortDate(String(value))} formatter={(_value, _name, item) => [words(String(item.payload.condition)), "Condition"]}/>
          <Bar isAnimationActive={false} dataKey="conditionBand" name="Condition" minPointSize={2}>{visibleData.map((point) => <Cell key={point.timestamp} fill={CONDITION_COLORS[point.condition] ?? CONDITION_COLORS.unknown}/>)}</Bar>
        </ComposedChart>
      </ResponsiveContainer></div>
      <div className="state-legend condition-legend">{conditions.map((name) => <span key={name}><i style={{ background: CONDITION_COLORS[name] ?? CONDITION_COLORS.unknown }}/>{words(name)}</span>)}</div>
    </section>
  </>;
}
