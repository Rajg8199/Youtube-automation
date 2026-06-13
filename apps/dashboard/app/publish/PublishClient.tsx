"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { PublishItem, PublishQuota } from "@/lib/worker";

function QuotaBar({ q }: { q: PublishQuota }) {
  const pct = q.daily ? Math.min(100, Math.round((q.used / q.daily) * 100)) : 0;
  return (
    <div className="rounded-lg border border-neutral-800 p-3 space-y-2">
      <div className="flex justify-between text-xs text-neutral-400">
        <span>YouTube API quota today</span>
        <span>{q.used} / {q.daily} units</span>
      </div>
      <div className="h-2 w-full rounded bg-neutral-800">
        <div className={`h-2 rounded ${pct > 80 ? "bg-red-500" : "bg-brand-orange"}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-neutral-500">
        {q.youtube_ready
          ? "API publishing enabled (refresh token present)."
          : "No refresh token — items produce a downloadable publish-kit. Run `make youtube-auth`."}
      </div>
    </div>
  );
}

export default function PublishClient({
  quota,
  items,
  base,
}: {
  quota: PublishQuota | null;
  items: PublishItem[];
  base: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);

  async function decide(id: string, action: "approve" | "reject") {
    setBusy(id);
    try {
      await fetch(`/api/content/${id}/publish-decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      router.refresh();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      {quota && <QuotaBar q={quota} />}
      {items.length === 0 ? (
        <p className="text-neutral-500">
          Nothing to publish yet. Finish a video in Studio, then run SEO
          (<code className="text-neutral-400">POST /jobs/seo_optimizer</code>).
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((it) => (
            <div key={it.id} className="rounded-lg border border-neutral-800 p-3 space-y-2">
              <div className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="truncate font-medium">{it.title || it.working_title}</div>
                  <div className="text-xs text-neutral-500">
                    <span className="text-neutral-400">{it.status}</span>
                    {it.tag_count ? ` · ${it.tag_count} tags` : ""}
                    {it.method ? ` · ${it.method}` : ""}
                    {it.youtube_video_id ? ` · ▶ ${it.youtube_video_id}` : ""}
                    {it.publish_note ? ` · ${it.publish_note}` : ""}
                  </div>
                </div>
                {it.status === "ready_for_review" && (
                  <>
                    <button
                      disabled={busy === it.id}
                      onClick={() => decide(it.id, "approve")}
                      className="rounded bg-brand-orange/90 px-2 py-1 text-xs font-medium text-black disabled:opacity-50"
                    >
                      Approve to publish
                    </button>
                    <button
                      disabled={busy === it.id}
                      onClick={() => decide(it.id, "reject")}
                      className="rounded border border-neutral-700 px-2 py-1 text-xs text-neutral-300 disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </>
                )}
                {it.youtube_video_id && (
                  <a
                    href={`https://youtube.com/watch?v=${it.youtube_video_id}`}
                    target="_blank" rel="noreferrer"
                    className="text-xs text-brand-orange underline"
                  >
                    open on YouTube
                  </a>
                )}
                {it.kit_path && (
                  <a
                    href={`${base}/media/${it.kit_path}`}
                    className="rounded border border-brand-orange px-2 py-1 text-xs text-brand-orange"
                  >
                    ⬇ publish kit
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
