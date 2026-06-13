import Link from "next/link";
import { getOverview } from "@/lib/worker";

export const dynamic = "force-dynamic";

function Kpi({ label, value, sub, href }: { label: string; value: string; sub?: string; href?: string }) {
  const body = (
    <div className="rounded-lg border border-neutral-800 p-4 hover:border-neutral-700 transition-colors">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-neutral-100">{value}</div>
      {sub && <div className="text-xs text-neutral-500 mt-0.5">{sub}</div>}
    </div>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

const SEV: Record<string, string> = {
  info: "text-neutral-500", warn: "text-yellow-500", error: "text-red-500", critical: "text-red-400",
};

export default async function CommandCenter() {
  const o = await getOverview();
  if (!o) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-2">Command Center</h1>
        <p className="text-neutral-500">Worker unreachable. Is it running on :8008?</p>
      </div>
    );
  }
  const k = o.kpis;
  const maxFunnel = Math.max(1, ...o.funnel.map((f) => f.count));
  const costPct = k.monthly_cap_usd ? Math.min(100, (k.cost_mtd_usd / k.monthly_cap_usd) * 100) : 0;

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Command Center</h1>
          <p className="text-neutral-500 text-sm">
            Tier: <span className="text-brand-orange">{k.stack_tier}</span> · pipeline at a glance
          </p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="In flight" value={String(k.in_flight)} sub="items in production" />
        <Kpi label="Scored topics" value={String(k.topics_scored)} sub={`${k.topics_greenlit} greenlit`} href="/research" />
        <Kpi label="Published" value={String(k.published_videos)} href="/videos" />
        <Kpi label="Cost (MTD)" value={`$${k.cost_mtd_usd.toFixed(2)}`} sub={`cap $${k.monthly_cap_usd}`} href="/insights" />
      </div>

      {/* Budget gauge */}
      <div className="rounded-lg border border-neutral-800 p-4">
        <div className="flex justify-between text-xs text-neutral-400 mb-2">
          <span>Monthly cost vs budget</span>
          <span>${k.cost_mtd_usd.toFixed(2)} / ${k.monthly_cap_usd}</span>
        </div>
        <div className="h-2 w-full rounded bg-neutral-800">
          <div className={`h-2 rounded ${costPct > 80 ? "bg-red-500" : "bg-brand-orange"}`} style={{ width: `${costPct}%` }} />
        </div>
        <div className="text-xs text-neutral-500 mt-2">
          YouTube quota today: {o.quota.used} / {o.quota.daily} units
        </div>
      </div>

      {/* Pipeline funnel */}
      <div>
        <h2 className="text-sm font-medium text-neutral-300 mb-3">Pipeline funnel</h2>
        <div className="space-y-1.5">
          {o.funnel.filter((f) => f.count > 0).length === 0 && (
            <p className="text-neutral-600 text-sm">Pipeline empty — greenlight a topic in Research.</p>
          )}
          {o.funnel.filter((f) => f.count > 0).map((f) => (
            <div key={f.status} className="flex items-center gap-3">
              <div className="w-32 text-xs text-neutral-400 text-right">{f.status}</div>
              <div className="flex-1 h-5 rounded bg-neutral-900">
                <div className="h-5 rounded bg-brand-orange/70 flex items-center justify-end pr-2"
                     style={{ width: `${(f.count / maxFunnel) * 100}%` }}>
                  <span className="text-[11px] text-black font-medium">{f.count}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent activity */}
      <div>
        <h2 className="text-sm font-medium text-neutral-300 mb-3">Recent activity</h2>
        <div className="rounded-lg border border-neutral-800 divide-y divide-neutral-900">
          {o.recent.length === 0 ? (
            <div className="p-3 text-sm text-neutral-600">No events yet.</div>
          ) : (
            o.recent.map((e, i) => (
              <div key={i} className="flex items-center gap-3 p-2.5 text-sm">
                <span className={`text-xs w-14 ${SEV[e.severity] ?? "text-neutral-500"}`}>{e.severity}</span>
                <span className="text-neutral-500 text-xs w-44 truncate">{e.component}</span>
                <span className="text-neutral-300 truncate flex-1">{e.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
