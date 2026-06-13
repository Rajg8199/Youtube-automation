import { getVideos } from "@/lib/worker";

export const dynamic = "force-dynamic";

export default async function VideosPage() {
  const videos = await getVideos(50);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Published</h1>
        <p className="text-neutral-500 text-sm">
          Published videos and their latest metrics. Metrics populate the morning after a real
          upload via the Analytics ingest (retention → script-segment mapping lands here).
        </p>
      </div>
      {videos.length === 0 ? (
        <p className="text-neutral-500">No published videos yet.</p>
      ) : (
        <div className="space-y-2">
          {videos.map((v) => (
            <div key={v.youtube_video_id} className="rounded-lg border border-neutral-800 p-3">
              <div className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <a
                    href={`https://youtube.com/watch?v=${v.youtube_video_id}`}
                    target="_blank" rel="noreferrer"
                    className="truncate font-medium text-brand-orange hover:underline block"
                  >
                    {v.working_title ?? v.youtube_video_id}
                  </a>
                  <div className="text-xs text-neutral-500">
                    {v.format ?? "long"}
                    {v.metrics_date ? ` · as of ${v.metrics_date}` : " · no metrics yet"}
                  </div>
                </div>
                <div className="text-right text-xs text-neutral-400">
                  <div>{v.views ?? 0} views · {v.likes ?? 0} likes</div>
                  <div>
                    {v.avg_pct_viewed != null ? `${Math.round(v.avg_pct_viewed)}% avg viewed` : "—"}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
