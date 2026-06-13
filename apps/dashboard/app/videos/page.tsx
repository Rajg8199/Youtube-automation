import { getVideos } from "@/lib/worker";
import { Card, PageHeader, EmptyState } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function VideosPage() {
  const videos = await getVideos(50);
  return (
    <>
      <PageHeader
        title="Published"
        subtitle="Published videos and their latest metrics. Metrics populate the morning after a real upload (retention → script-segment mapping lands here)."
      />
      {videos.length === 0 ? (
        <EmptyState>No published videos yet.</EmptyState>
      ) : (
        <div className="space-y-2">
          {videos.map((v) => (
            <Card key={v.youtube_video_id} className="p-4">
              <div className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <a
                    href={`https://youtube.com/watch?v=${v.youtube_video_id}`}
                    target="_blank" rel="noreferrer"
                    className="truncate font-medium text-brand-orange hover:underline block"
                  >
                    {v.working_title ?? v.youtube_video_id}
                  </a>
                  <div className="text-xs text-fg-subtle mt-0.5">
                    {v.format ?? "long"}
                    {v.metrics_date ? ` · as of ${v.metrics_date}` : " · no metrics yet"}
                  </div>
                </div>
                <div className="text-right text-xs text-fg-muted tnum">
                  <div>{v.views ?? 0} views · {v.likes ?? 0} likes</div>
                  <div>{v.avg_pct_viewed != null ? `${Math.round(v.avg_pct_viewed)}% avg viewed` : "—"}</div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
