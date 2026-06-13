import { getPublishQueue, mediaBase } from "@/lib/worker";
import { PageHeader } from "@/components/ui";
import PublishClient from "./PublishClient";

export const dynamic = "force-dynamic";

export default async function PublishPage() {
  const { quota, items } = await getPublishQueue();
  return (
    <>
      <PageHeader
        title="Publish Queue"
        subtitle="Approve a finished video to publish. With a YouTube token it uploads via the API (quota-tracked); otherwise it builds a one-click publish-kit."
      />
      <PublishClient quota={quota} items={items} base={mediaBase} />
    </>
  );
}
