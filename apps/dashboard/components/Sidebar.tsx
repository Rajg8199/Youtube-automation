"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV: { href: string; label: string; icon: string }[] = [
  { href: "/", label: "Command Center", icon: "◎" },
  { href: "/research", label: "Research", icon: "🔍" },
  { href: "/scripts", label: "Scripts", icon: "✍" },
  { href: "/studio", label: "Studio", icon: "🎬" },
  { href: "/publish", label: "Publish", icon: "📤" },
  { href: "/videos", label: "Published", icon: "▶" },
  { href: "/insights", label: "Insights", icon: "🧠" },
  { href: "/system", label: "System", icon: "⚙" },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-56 shrink-0 border-r border-neutral-800 bg-neutral-950 min-h-screen p-4">
      <div className="px-2 pb-5">
        <div className="text-brand-orange font-bold leading-tight">PhoneWala</div>
        <div className="text-neutral-500 text-sm leading-tight">Gyan · Control</div>
      </div>
      <nav className="space-y-1">
        {NAV.map((n) => {
          const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm ${
                active
                  ? "bg-brand-orange/15 text-brand-orange font-medium"
                  : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200"
              }`}
            >
              <span className="w-4 text-center">{n.icon}</span>
              {n.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
