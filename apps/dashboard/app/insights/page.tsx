import { getAutonomy, getInsights } from "@/lib/worker";
import { PageHeader } from "@/components/ui";
import InsightsClient from "./InsightsClient";

export const dynamic = "force-dynamic";

export default async function InsightsPage() {
  const [{ insights, recommendations }, { gates, guardrails }] = await Promise.all([
    getInsights(),
    getAutonomy(),
  ]);
  return (
    <>
      <PageHeader
        title="Insights & Strategy"
        subtitle="What the system learned from published performance, the Growth Strategist’s recommendations, and the autonomy dial (manual → auto-with-veto → full-auto, gated by earned trust)."
      />
      <InsightsClient
        insights={insights}
        recommendations={recommendations}
        gates={gates}
        guardrails={guardrails}
      />
    </>
  );
}
