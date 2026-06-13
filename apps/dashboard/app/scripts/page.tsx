import { getScripts } from "@/lib/worker";
import { PageHeader } from "@/components/ui";
import ScriptsClient from "./ScriptsClient";

export const dynamic = "force-dynamic";

export default async function ScriptsPage() {
  const items = await getScripts(100);
  return (
    <>
      <PageHeader
        title="Scripts"
        subtitle="Hinglish scripts with fact-check results. QA is a hard gate — every concrete claim must trace to the research brief. Approve a passed script to send it to production."
      />
      <ScriptsClient items={items} />
    </>
  );
}
