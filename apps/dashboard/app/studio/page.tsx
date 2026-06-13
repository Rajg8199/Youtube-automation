import { getStudioItems, mediaBase } from "@/lib/worker";
import { PageHeader } from "@/components/ui";
import StudioClient from "./StudioClient";

export const dynamic = "force-dynamic";

export default async function StudioPage() {
  const items = await getStudioItems(50);
  return (
    <>
      <PageHeader
        title="Studio"
        subtitle="Production output for approved scripts: voiceover, scene plan, the rendered 1080p video, and thumbnail variants."
      />
      <StudioClient items={items} base={mediaBase} />
    </>
  );
}
