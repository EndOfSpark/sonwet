"use client";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="error-page"><div className="error-card"><span>SONWET / DATABASE ERROR</span><h1>The archive could not be opened.</h1><p>{error.message}</p><button onClick={reset}>Try again</button><small>Set SQLITE_PATH to the collector&apos;s weather_data.db file.</small></div></main>;
}
