"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ScriptItem } from "@/lib/worker";

const STATUS_STYLE: Record<string, string> = {
  script_approved: "text-green-500",
  qa_failed: "text-red-500",
  script_qa: "text-yellow-500",
  scripting: "text-neutral-400",
};

function Badge({ status }: { status: string }) {
  return (
    <span className={`text-xs font-medium ${STATUS_STYLE[status] ?? "text-neutral-400"}`}>
      {status}
    </span>
  );
}

function Card({
  item,
  onDecide,
  busy,
}: {
  item: ScriptItem;
  onDecide: (id: string, action: "approve" | "request_changes" | "reject", note?: string) => void;
  busy: string | null;
}) {
  const [open, setOpen] = useState(false);
  const failures = item.claims_failed ?? [];
  const flags = item.policy_flags ?? [];
  const mins = item.est_duration_sec ? Math.round(item.est_duration_sec / 6) / 10 : null;

  return (
    <div className="rounded-lg border border-neutral-800 p-4 space-y-2">
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="truncate font-medium">{item.working_title}</div>
          <div className="text-xs text-neutral-500">
            <Badge status={item.status} /> · {item.format} · v{item.version ?? "—"} ·{" "}
            {item.word_count ?? "—"} words{mins ? ` · ~${mins} min` : ""}
            {item.approval_status ? ` · gate: ${item.approval_status}` : ""}
          </div>
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-xs text-neutral-400 hover:text-neutral-200"
        >
          {open ? "hide script" : "view script"}
        </button>
      </div>

      {/* QA findings */}
      {item.passed === false && (
        <div className="rounded border border-red-900/50 bg-red-950/30 p-2 text-sm">
          <div className="text-red-400 font-medium">
            QA failed — {failures.length} unverified claim{failures.length === 1 ? "" : "s"}
          </div>
          <ul className="mt-1 list-disc pl-5 text-neutral-300 text-xs space-y-0.5">
            {failures.map((f, i) => (
              <li key={i}>
                <span className="text-red-300">{f.claim}</span> — {f.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
      {item.passed === true && (
        <div className="text-sm text-green-500">
          ✓ QA passed — {item.claims_checked ?? 0} claims checked, 0 unverified
        </div>
      )}
      {flags.length > 0 && (
        <div className="text-xs text-yellow-500">
          {flags.map((f, i) => (
            <div key={i}>⚑ {f.type}: {f.note}</div>
          ))}
        </div>
      )}

      {open && (
        <div className="space-y-2 border-t border-neutral-800 pt-2">
          {item.angle && (
            <p className="text-xs text-neutral-500">
              <span className="text-neutral-400">Angle:</span> {item.angle}
            </p>
          )}
          <p className="text-sm">
            <span className="text-brand-orange">HOOK · </span>
            {item.hook}
          </p>
          <pre className="whitespace-pre-wrap text-sm text-neutral-300 font-sans">
            {item.body_markdown}
          </pre>
          {item.cta && <p className="text-sm text-neutral-400">CTA · {item.cta}</p>}
        </div>
      )}

      {/* Script gate */}
      {item.status === "script_approved" && item.approval_status !== "approved" && (
        <div className="flex gap-2 pt-1">
          <button
            disabled={busy === item.id}
            onClick={() => onDecide(item.id, "approve")}
            className="rounded bg-brand-orange/90 px-2 py-1 text-xs font-medium text-black disabled:opacity-50"
          >
            Approve script
          </button>
          <button
            disabled={busy === item.id}
            onClick={() => onDecide(item.id, "request_changes", "Please revise.")}
            className="rounded border border-neutral-700 px-2 py-1 text-xs text-neutral-300 disabled:opacity-50"
          >
            Request changes
          </button>
          <button
            disabled={busy === item.id}
            onClick={() => onDecide(item.id, "reject")}
            className="rounded border border-neutral-800 px-2 py-1 text-xs text-neutral-500 disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}

export default function ScriptsClient({ items }: { items: ScriptItem[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);

  async function onDecide(
    id: string,
    action: "approve" | "request_changes" | "reject",
    note?: string,
  ) {
    setBusy(id);
    try {
      await fetch(`/api/content/${id}/script-decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, note }),
      });
      router.refresh();
    } finally {
      setBusy(null);
    }
  }

  if (items.length === 0) {
    return (
      <p className="text-neutral-500">
        No scripts yet. Greenlight a topic in the Research Queue, then run the script pipeline
        (<code className="text-neutral-400">POST /jobs/script_pipeline</code>).
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <Card key={item.id} item={item} onDecide={onDecide} busy={busy} />
      ))}
    </div>
  );
}
