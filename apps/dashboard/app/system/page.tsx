// Server component: fetches worker /health each load. The only live view in Phase 0.

async function getHealth(): Promise<{
  status: string;
  version: string;
  stack_tier: string;
  db: string;
} | null> {
  const url = `${process.env.WORKER_URL ?? "http://localhost:8000"}/health`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    return await res.json();
  } catch {
    return null;
  }
}

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-3 w-3 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`}
    />
  );
}

export default async function SystemPage() {
  const h = await getHealth();
  const workerUp = h !== null;
  const dbUp = h?.db === "up";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">System</h1>
      <div className="rounded-lg border border-neutral-800 p-4 space-y-3 max-w-md">
        <div className="flex items-center gap-3">
          <Dot ok={workerUp} />
          <span>Worker API {workerUp ? `(v${h?.version})` : "unreachable"}</span>
        </div>
        <div className="flex items-center gap-3">
          <Dot ok={dbUp} />
          <span>Database {dbUp ? "connected" : "down"}</span>
        </div>
        {h && (
          <div className="text-sm text-neutral-500">
            stack tier: <span className="text-neutral-300">{h.stack_tier}</span>
          </div>
        )}
      </div>
      <p className="text-neutral-500 text-sm">
        Kill switch, workflow history, quota, and event log arrive in Phase 5.
      </p>
    </div>
  );
}
