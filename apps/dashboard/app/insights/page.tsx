import { getAutonomy, getInsights } from "@/lib/worker";
import InsightsClient from "./InsightsClient";

export const dynamic = "force-dynamic";

export default async function InsightsPage() {
  const [{ insights, recommendations }, { gates, guardrails }] = await Promise.all([
    getInsights(),
    getAutonomy(),
  ]);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Insights & Strategy</h1>
        <p className="text-neutral-500 text-sm">
          What the system has learned from published performance, the Growth Strategist&apos;s
          recommendations, and the autonomy dial (manual → auto-with-veto → full-auto, gated by
          earned trust).
        </p>
      </div>
      <InsightsClient
        insights={insights}
        recommendations={recommendations}
        gates={gates}
        guardrails={guardrails}
      />
    </div>
  );
}
