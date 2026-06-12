import { getScoredTopics, getRecentSignals } from "@/lib/worker";
import ResearchClient from "./ResearchClient";

export const dynamic = "force-dynamic";

export default async function ResearchPage() {
  const [topics, signals] = await Promise.all([
    getScoredTopics(100),
    getRecentSignals(50),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Research Queue</h1>
        <p className="text-neutral-500 text-sm">
          Scored topics ranked by composite. Expand “why?” for the factor breakdown and
          rationale. Greenlight to convert into a content item (Editorial Planner, Phase 2).
        </p>
      </div>
      <ResearchClient topics={topics} signals={signals} />
    </div>
  );
}
