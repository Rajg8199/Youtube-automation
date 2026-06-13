import { Card, PageHeader, Dot, Badge } from "@/components/ui";

async function getHealth(): Promise<{ status: string; version: string; stack_tier: string; db: string } | null> {
  const url = `${process.env.WORKER_URL ?? "http://localhost:8008"}/health`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    return await res.json();
  } catch {
    return null;
  }
}

function Row({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <div className="flex items-center gap-3">
        <Dot tone={ok ? "ok" : "danger"} />
        <span className="text-sm text-fg">{label}</span>
      </div>
      <span className="text-xs text-fg-muted">{detail}</span>
    </div>
  );
}

export default async function SystemPage() {
  const h = await getHealth();
  const workerUp = h !== null;
  const dbUp = h?.db === "up";

  return (
    <>
      <PageHeader title="System" subtitle="Service health and runtime configuration." />
      <Card className="max-w-xl divide-y divide-line">
        <Row label="Worker API" ok={workerUp} detail={workerUp ? `v${h?.version}` : "unreachable"} />
        <Row label="Database" ok={dbUp} detail={dbUp ? "connected" : "down"} />
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-sm text-fg">Stack tier</span>
          {h ? <Badge tone="brand">{h.stack_tier}</Badge> : <span className="text-xs text-fg-subtle">—</span>}
        </div>
      </Card>
      <p className="text-fg-subtle text-sm mt-4">
        Schedulers run in n8n (localhost:5678). Kill switch: stop the n8n container or toggle
        workflows inactive.
      </p>
    </>
  );
}
