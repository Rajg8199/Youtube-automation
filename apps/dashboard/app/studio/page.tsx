import { getStudioItems, mediaBase } from "@/lib/worker";
import StudioClient from "./StudioClient";

export const dynamic = "force-dynamic";

export default async function StudioPage() {
  const items = await getStudioItems(50);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Studio</h1>
        <p className="text-neutral-500 text-sm">
          Production output for approved scripts: voiceover (Edge TTS), scene plan, the rendered
          1080p video, and thumbnail variants — all generated free.
        </p>
      </div>
      <StudioClient items={items} base={mediaBase} />
    </div>
  );
}
