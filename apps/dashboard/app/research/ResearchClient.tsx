"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ScoredTopic, Signal } from "@/lib/worker";

const FACTORS: { key: keyof ScoredTopic; label: string }[] = [
  { key: "trend_velocity", label: "Trend" },
  { key: "search_demand", label: "Demand" },
  { key: "competition_gap", label: "Gap" },
  { key: "channel_fit", label: "Fit" },
  { key: "monetization_potential", label: "Money" },
  { key: "freshness", label: "Fresh" },
];

function Bar({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="h-1.5 w-full rounded bg-surface-2">
      <div className="h-1.5 rounded bg-brand-orange" style={{ width: `${pct}%` }} />
    </div>
  );
}

function TopicRow({ t, onDecide, busy }: {
  t: ScoredTopic;
  onDecide: (id: string, action: "greenlight" | "reject") => void;
  busy: string | null;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-line p-3">
      <div className="flex items-center gap-3">
        <div className="text-brand-orange font-mono text-lg w-14 text-right">
          {Number(t.composite).toFixed(2)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="truncate font-medium">{t.title}</div>
          <div className="text-xs text-fg-muted">
            {t.category ?? "uncategorized"} · {t.signal_count} signal
            {t.signal_count === 1 ? "" : "s"}
            {t.brands?.length ? ` · ${t.brands.join(", ")}` : ""}
          </div>
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-xs text-fg-muted hover:text-fg"
        >
          {open ? "hide" : "why?"}
        </button>
        {t.status === "selected" ? (
          <span className="text-xs text-ok px-2">✓ greenlit</span>
        ) : (
          <>
            <button
              disabled={busy === t.id}
              onClick={() => onDecide(t.id, "greenlight")}
              className="rounded bg-brand-orange/90 px-2 py-1 text-xs font-medium text-black disabled:opacity-50"
            >
              Greenlight
            </button>
            <button
              disabled={busy === t.id}
              onClick={() => onDecide(t.id, "reject")}
              className="rounded border border-line-strong px-2 py-1 text-xs text-fg disabled:opacity-50"
            >
              Reject
            </button>
          </>
        )}
      </div>
      {open && (
        <div className="mt-3 space-y-2">
          <div className="grid grid-cols-6 gap-2">
            {FACTORS.map((f) => (
              <div key={f.key} className="space-y-1">
                <div className="text-[10px] uppercase text-fg-muted">{f.label}</div>
                <Bar value={Number(t[f.key])} />
                <div className="text-[10px] text-fg-muted">
                  {Number(t[f.key]).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
          {t.rationale && (
            <p className="text-sm text-fg italic">“{t.rationale}”</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function ResearchClient({
  topics,
  signals,
}: {
  topics: ScoredTopic[];
  signals: Signal[];
}) {
  const router = useRouter();
  const [tab, setTab] = useState<"topics" | "signals">("topics");
  const [busy, setBusy] = useState<string | null>(null);

  async function onDecide(id: string, action: "greenlight" | "reject") {
    setBusy(id);
    try {
      await fetch(`/api/topics/${id}/decision`, {
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
      <div className="flex gap-4 border-b border-line">
        {(["topics", "signals"] as const).map((k) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`pb-2 text-sm ${
              tab === k
                ? "border-b-2 border-brand-orange text-fg"
                : "text-fg-muted"
            }`}
          >
            {k === "topics" ? `Scored topics (${topics.length})` : `Signal firehose (${signals.length})`}
          </button>
        ))}
      </div>

      {tab === "topics" ? (
        topics.length === 0 ? (
          <p className="text-fg-muted">
            No scored topics yet. Run the research sweep + trend scout + topic scorer
            (WF1/WF2), then refresh.
          </p>
        ) : (
          <div className="space-y-2">
            {topics.map((t) => (
              <TopicRow key={t.id} t={t} onDecide={onDecide} busy={busy} />
            ))}
          </div>
        )
      ) : (
        <div className="divide-y divide-line">
          {signals.map((s) => (
            <a
              key={s.id}
              href={s.url ?? "#"}
              target="_blank"
              rel="noreferrer"
              className="block py-2 hover:bg-surface-2/50"
            >
              <div className="truncate text-sm">{s.title}</div>
              <div className="text-xs text-fg-muted">
                {s.source ?? "?"} · {s.processed ? "processed" : "pending"}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
