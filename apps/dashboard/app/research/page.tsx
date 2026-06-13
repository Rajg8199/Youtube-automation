import { getScoredTopics, getRecentSignals } from "@/lib/worker";
import { PageHeader } from "@/components/ui";
import ResearchClient from "./ResearchClient";

export const dynamic = "force-dynamic";

export default async function ResearchPage() {
  const [topics, signals] = await Promise.all([
    getScoredTopics(100),
    getRecentSignals(50),
  ]);

  return (
    <>
      <PageHeader
        title="Research Queue"
        subtitle="Scored topics ranked by composite. Expand “why?” for the factor breakdown and rationale; greenlight to convert into a content item."
      />
      <ResearchClient topics={topics} signals={signals} />
    </>
  );
}
