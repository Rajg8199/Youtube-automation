"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { AutonomyGate, Guardrails, Insight, Recommendation } from "@/lib/worker";

const MODES = ["manual", "auto_with_veto", "full_auto"] as const;

function AutonomyDial({
  gates,
  guardrails,
}: {
  gates: AutonomyGate[];
  guardrails: Guardrails | null;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function set(gate: string, mode: string) {
    setBusy(gate + mode);
    setErr(null);
    try {
      const res = await fetch("/api/autonomy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gate, mode }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        setErr(j.detail || "change blocked");
      } else {
        router.refresh();
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-lg border border-line p-4 space-y-3">
      <div className="font-medium">Autonomy dial</div>
      {guardrails && (
        <div className="text-xs text-fg-muted">
          full_auto needs ≥{guardrails.thresholds.min_published} published (have{" "}
          {guardrails.published}), ≥{Math.round(guardrails.thresholds.min_qa_pass_rate * 100)}% QA
          pass (have {Math.round(guardrails.qa_pass_rate * 100)}%), 0 policy flags/30d (have{" "}
          {guardrails.policy_flags_30d}) ·{" "}
          <span className={guardrails.full_auto_eligible ? "text-ok" : "text-danger"}>
            {guardrails.full_auto_eligible ? "eligible" : "not eligible"}
          </span>
        </div>
      )}
      {err && <div className="text-xs text-danger">{err}</div>}
      <div className="space-y-2">
        {gates.map((g) => (
          <div key={g.gate} className="flex items-center gap-2">
            <div className="w-36 text-sm text-fg">{g.gate}</div>
            <div className="flex gap-1">
              {MODES.map((m) => (
                <button
                  key={m}
                  disabled={busy !== null}
                  onClick={() => set(g.gate, m)}
                  className={`rounded px-2 py-1 text-xs ${
                    g.mode === m
                      ? "bg-brand-orange text-black font-medium"
                      : "border border-line-strong text-fg-muted"
                  } disabled:opacity-50`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function InsightsClient({
  insights,
  recommendations,
  gates,
  guardrails,
}: {
  insights: Insight[];
  recommendations: Recommendation[];
  gates: AutonomyGate[];
  guardrails: Guardrails | null;
}) {
  return (
    <div className="space-y-6">
      <AutonomyDial gates={gates} guardrails={guardrails} />

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <div className="font-medium">Recommendations</div>
          {recommendations.length === 0 ? (
            <p className="text-fg-subtle text-sm">None yet — run the Growth Strategist.</p>
          ) : (
            recommendations.map((r) => (
              <div key={r.id} className="rounded border border-line p-2">
                <div className="text-sm">
                  <span className="text-brand-orange text-xs">[{r.type}]</span> {r.title}
                </div>
                {r.detail && <div className="text-xs text-fg-muted">{r.detail}</div>}
              </div>
            ))
          )}
        </div>

        <div className="space-y-2">
          <div className="font-medium">Insights</div>
          {insights.length === 0 ? (
            <p className="text-fg-subtle text-sm">None yet — run the learning loop after videos publish.</p>
          ) : (
            insights.map((i) => (
              <div key={i.id} className="rounded border border-line p-2 text-sm text-fg">
                <span className="text-xs text-fg-muted">[{i.scope}]</span> {i.insight}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
