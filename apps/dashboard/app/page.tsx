import { getOverview } from "@/lib/worker";
import { Card, PageHeader, SectionTitle, StatCard, Progress, EmptyState } from "@/components/ui";
import { Layers, Sparkles, PlaySquare, DollarSign, Activity } from "lucide-react";

export const dynamic = "force-dynamic";

const SEV: Record<string, string> = {
  info: "text-fg-subtle", warn: "text-warn", error: "text-danger", critical: "text-danger",
};

export default async function CommandCenter() {
  const o = await getOverview();
  if (!o) {
    return (
      <>
        <PageHeader title="Command Center" subtitle="Pipeline at a glance" />
        <EmptyState>Worker unreachable — is it running on :8008?</EmptyState>
      </>
    );
  }
  const k = o.kpis;
  const maxFunnel = Math.max(1, ...o.funnel.map((f) => f.count));
  const costPct = k.monthly_cap_usd ? (k.cost_mtd_usd / k.monthly_cap_usd) * 100 : 0;
  const quotaPct = o.quota.daily ? (o.quota.used / o.quota.daily) * 100 : 0;
  const nonzero = o.funnel.filter((f) => f.count > 0);

  return (
    <>
      <PageHeader
        title="Command Center"
        subtitle="Live view of the content pipeline — research to published."
        actions={
          <span className="inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs text-fg-muted">
            tier <span className="text-brand-orange font-medium">{k.stack_tier}</span>
          </span>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="In flight" value={String(k.in_flight)} sub="items in production" icon={<Layers className="h-4 w-4" />} accent />
        <StatCard label="Scored topics" value={String(k.topics_scored)} sub={`${k.topics_greenlit} greenlit`} icon={<Sparkles className="h-4 w-4" />} />
        <StatCard label="Published" value={String(k.published_videos)} sub="videos live" icon={<PlaySquare className="h-4 w-4" />} />
        <StatCard label="Cost (MTD)" value={`$${k.cost_mtd_usd.toFixed(2)}`} sub={`of $${k.monthly_cap_usd} cap`} icon={<DollarSign className="h-4 w-4" />} />
      </div>

      <div className="grid lg:grid-cols-3 gap-4 mt-4">
        {/* Budget + quota */}
        <Card className="p-5 lg:col-span-1">
          <SectionTitle>Budget & quota</SectionTitle>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs text-fg-muted mb-1.5">
                <span>Monthly cost</span>
                <span className="tnum">${k.cost_mtd_usd.toFixed(2)} / ${k.monthly_cap_usd}</span>
              </div>
              <Progress value={costPct} tone={costPct > 80 ? "danger" : "brand"} />
            </div>
            <div>
              <div className="flex justify-between text-xs text-fg-muted mb-1.5">
                <span>YouTube quota (today)</span>
                <span className="tnum">{o.quota.used} / {o.quota.daily}</span>
              </div>
              <Progress value={quotaPct} tone={quotaPct > 80 ? "warn" : "ok"} />
            </div>
          </div>
        </Card>

        {/* Pipeline funnel */}
        <Card className="p-5 lg:col-span-2">
          <SectionTitle>Pipeline funnel</SectionTitle>
          {nonzero.length === 0 ? (
            <p className="text-sm text-fg-muted py-4">Pipeline empty — greenlight a topic in Research.</p>
          ) : (
            <div className="space-y-2">
              {nonzero.map((f) => (
                <div key={f.status} className="flex items-center gap-3">
                  <div className="w-32 text-xs text-fg-muted text-right truncate">{f.status}</div>
                  <div className="flex-1 h-6 rounded-md bg-surface-2 overflow-hidden">
                    <div
                      className="h-full rounded-md bg-gradient-to-r from-brand-orangeDim to-brand-orange flex items-center justify-end pr-2 min-w-[1.5rem]"
                      style={{ width: `${(f.count / maxFunnel) * 100}%` }}
                    >
                      <span className="text-[11px] text-black font-semibold tnum">{f.count}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Activity */}
      <div className="mt-4">
        <SectionTitle right={<Activity className="h-3.5 w-3.5 text-fg-subtle" />}>Recent activity</SectionTitle>
        <Card>
          {o.recent.length === 0 ? (
            <div className="p-5 text-sm text-fg-muted">No events yet.</div>
          ) : (
            <div className="divide-y divide-line">
              {o.recent.map((e, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                  <span className={`text-[11px] w-12 font-medium ${SEV[e.severity] ?? "text-fg-subtle"}`}>{e.severity}</span>
                  <span className="text-fg-subtle text-xs w-48 truncate font-mono">{e.component}</span>
                  <span className="text-fg-muted truncate flex-1">{e.message}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
