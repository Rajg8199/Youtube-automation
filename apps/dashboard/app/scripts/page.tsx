import { getScripts } from "@/lib/worker";
import ScriptsClient from "./ScriptsClient";

export const dynamic = "force-dynamic";

export default async function ScriptsPage() {
  const items = await getScripts(100);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Scripts</h1>
        <p className="text-neutral-500 text-sm">
          Hinglish scripts with their fact-check results. QA is a hard gate — every concrete
          claim must trace to the research brief. Approve a passed script to send it to
          production (Phase 3).
        </p>
      </div>
      <ScriptsClient items={items} />
    </div>
  );
}
