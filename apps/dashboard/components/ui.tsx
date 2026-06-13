import type { ReactNode } from "react";

export function cn(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("rounded-xl border border-line bg-surface shadow-card", className)}>
      {children}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-fg">{title}</h1>
        {subtitle && <p className="text-sm text-fg-muted mt-1 max-w-2xl">{subtitle}</p>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  );
}

export function SectionTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-fg-subtle">{children}</h2>
      {right}
    </div>
  );
}

const TONES: Record<string, string> = {
  neutral: "bg-surface-2 text-fg-muted border-line",
  brand: "bg-brand-orange/12 text-brand-orange border-brand-orange/30",
  ok: "bg-ok/10 text-ok border-ok/30",
  warn: "bg-warn/10 text-warn border-warn/30",
  danger: "bg-danger/10 text-danger border-danger/30",
  info: "bg-info/10 text-info border-info/30",
};

export function Badge({ tone = "neutral", children }: { tone?: keyof typeof TONES | string; children: ReactNode }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium", TONES[tone] ?? TONES.neutral)}>
      {children}
    </span>
  );
}

export function Dot({ tone = "ok" }: { tone?: "ok" | "warn" | "danger" | "neutral" }) {
  const c = { ok: "bg-ok", warn: "bg-warn", danger: "bg-danger", neutral: "bg-fg-subtle" }[tone];
  return <span className={cn("inline-block h-2 w-2 rounded-full", c, tone === "ok" && "animate-pulsedot")} />;
}

export function Progress({ value, tone = "brand" }: { value: number; tone?: "brand" | "ok" | "warn" | "danger" }) {
  const pct = Math.max(0, Math.min(100, value));
  const c = { brand: "bg-brand-orange", ok: "bg-ok", warn: "bg-warn", danger: "bg-danger" }[tone];
  return (
    <div className="h-2 w-full rounded-full bg-surface-2 overflow-hidden">
      <div className={cn("h-full rounded-full transition-all", c)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function StatCard({
  label, value, sub, icon, accent,
}: { label: string; value: string; sub?: string; icon?: ReactNode; accent?: boolean }) {
  return (
    <Card className="p-4 hover:border-line-strong transition-colors animate-fade-up">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">{label}</span>
        {icon && <span className={cn("text-fg-subtle", accent && "text-brand-orange")}>{icon}</span>}
      </div>
      <div className={cn("mt-2 text-2xl font-semibold tnum", accent ? "text-brand-orange" : "text-fg")}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-fg-muted">{sub}</div>}
    </Card>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <Card className="p-8 text-center text-sm text-fg-muted border-dashed">{children}</Card>
  );
}
