import { useEffect, useState } from "react";

type Health = { status: string; version: string };

export function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetch("/api/health")
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`health ${res.status}`);
        }
        return (await res.json()) as Health;
      })
      .then(setHealth)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "health check failed");
      });
  }, []);

  return (
    <main className="shell">
      <header>
        <p className="eyebrow">Meta Global AI Developer Hackathon</p>
        <h1>BenchGuard</h1>
        <p className="tagline">A second pair of eyes for anyone working with their hands.</p>
      </header>
      <section aria-labelledby="api-status">
        <h2 id="api-status">API status</h2>
        {health ? (
          <p className="ok">
            <span aria-hidden="true">●</span> Online — {health.status} (v{health.version})
          </p>
        ) : error ? (
          <p className="warn">
            <span aria-hidden="true">▲</span> Unreachable — {error}. Start the backend on :8000.
          </p>
        ) : (
          <p>Checking…</p>
        )}
      </section>
      <section>
        <h2>Phase 0</h2>
        <p>
          Contracts, lint, and this shell are in place. Camera, compile, and the step engine come
          in later phases.
        </p>
      </section>
    </main>
  );
}
