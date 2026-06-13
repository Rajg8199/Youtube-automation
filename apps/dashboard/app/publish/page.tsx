import { getPublishQueue, mediaBase } from "@/lib/worker";
import PublishClient from "./PublishClient";

export const dynamic = "force-dynamic";

export default async function PublishPage() {
  const { quota, items } = await getPublishQueue();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Publish Queue</h1>
        <p className="text-neutral-500 text-sm">
          Approve a finished video to publish. With a YouTube refresh token it uploads via the
          API (quota-tracked); otherwise it builds a one-click publish-kit to upload by hand.
        </p>
      </div>
      <PublishClient quota={quota} items={items} base={mediaBase} />
    </div>
  );
}
