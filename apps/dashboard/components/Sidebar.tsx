"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Search, FileText, Clapperboard, Upload,
  PlaySquare, Brain, Settings, type LucideIcon,
} from "lucide-react";
import { cn } from "./ui";

type Item = { href: string; label: string; icon: LucideIcon };
const GROUPS: { title: string; items: Item[] }[] = [
  {
    title: "Pipeline",
    items: [
      { href: "/", label: "Command Center", icon: LayoutDashboard },
      { href: "/research", label: "Research", icon: Search },
      { href: "/scripts", label: "Scripts", icon: FileText },
      { href: "/studio", label: "Studio", icon: Clapperboard },
      { href: "/publish", label: "Publish", icon: Upload },
      { href: "/videos", label: "Published", icon: PlaySquare },
    ],
  },
  {
    title: "Intelligence",
    items: [{ href: "/insights", label: "Insights", icon: Brain }],
  },
  {
    title: "Ops",
    items: [{ href: "/system", label: "System", icon: Settings }],
  },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-60 shrink-0 border-r border-line bg-surface/60 backdrop-blur min-h-dvh sticky top-0 flex flex-col">
      <div className="flex items-center gap-2.5 px-5 h-16 border-b border-line">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-orange text-black font-bold text-sm">P</div>
        <div className="leading-tight">
          <div className="text-sm font-semibold text-fg">PhoneWala Gyan</div>
          <div className="text-[11px] text-fg-subtle">Content Control</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {GROUPS.map((g) => (
          <div key={g.title}>
            <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
              {g.title}
            </div>
            <div className="space-y-0.5">
              {g.items.map((n) => {
                const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
                const Icon = n.icon;
                return (
                  <Link
                    key={n.href}
                    href={n.href}
                    className={cn(
                      "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                      active
                        ? "bg-brand-orange/12 text-brand-orange font-medium"
                        : "text-fg-muted hover:bg-surface-2 hover:text-fg",
                    )}
                  >
                    {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-brand-orange" />}
                    <Icon className={cn("h-4 w-4", active ? "text-brand-orange" : "text-fg-subtle group-hover:text-fg")} />
                    {n.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-line px-5 py-3">
        <div className="flex items-center gap-2 text-xs text-fg-muted">
          <span className="inline-block h-2 w-2 rounded-full bg-ok animate-pulsedot" />
          <span>free tier · live</span>
        </div>
      </div>
    </aside>
  );
}
