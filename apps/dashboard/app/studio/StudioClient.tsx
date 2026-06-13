"use client";

import type { StudioItem } from "@/lib/worker";

function url(base: string, path: string | null): string | null {
  return path ? `${base}/media/${path}` : null;
}

function Card({ item, base }: { item: StudioItem; base: string }) {
  const video = url(base, item.video_path);
  const voice = url(base, item.voiceover_path);
  const scenes = item.scenes ?? [];
  const thumbs = item.thumbnails ?? [];

  return (
    <div className="rounded-lg border border-line p-4 space-y-3">
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="truncate font-medium">{item.working_title}</div>
          <div className="text-xs text-fg-muted">
            <span className="text-fg-muted">{item.status}</span> · {item.format}
            {item.video_duration ? ` · ${Math.round(item.video_duration)}s video` : ""}
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Final video preview */}
        <div className="space-y-2">
          <div className="text-xs uppercase text-fg-muted">Final video</div>
          {video ? (
            <video src={video} controls className="w-full rounded border border-line" />
          ) : (
            <div className="text-sm text-fg-subtle">not rendered yet</div>
          )}
          {voice && (
            <>
              <div className="text-xs uppercase text-fg-muted pt-1">Voiceover</div>
              <audio src={voice} controls className="w-full" />
            </>
          )}
        </div>

        {/* Thumbnails */}
        <div className="space-y-2">
          <div className="text-xs uppercase text-fg-muted">Thumbnails (A/B/C)</div>
          {thumbs.length ? (
            <div className="grid grid-cols-3 gap-2">
              {thumbs.map((t) => {
                const src = url(base, t.path);
                return (
                  <div key={t.variant} className="space-y-1">
                    {src && (
                      <img
                        src={src}
                        alt={`variant ${t.variant}`}
                        className={`w-full rounded border ${t.selected ? "border-brand-orange" : "border-line"}`}
                      />
                    )}
                    <div className="text-[10px] text-fg-muted">
                      {t.variant}{t.selected ? " ★" : ""}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-sm text-fg-subtle">not designed yet</div>
          )}
        </div>
      </div>

      {/* Scene timeline */}
      {scenes.length > 0 && (
        <div>
          <div className="text-xs uppercase text-fg-muted mb-1">
            Scene plan ({scenes.length})
          </div>
          <div className="flex flex-wrap gap-1">
            {scenes.map((s) => (
              <span
                key={s.idx}
                className="rounded bg-surface-2 border border-line px-2 py-0.5 text-[11px] text-fg-muted"
                title={s.caption}
              >
                {s.idx}. {s.template} · {Math.round(s.duration)}s
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function StudioClient({
  items,
  base,
}: {
  items: StudioItem[];
  base: string;
}) {
  if (items.length === 0) {
    return (
      <p className="text-fg-muted">
        Nothing in production yet. Approve a script in the Scripts tab, then run the production
        pipeline (<code className="text-fg-muted">POST /jobs/production_pipeline</code>).
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <Card key={item.id} item={item} base={base} />
      ))}
    </div>
  );
}
