import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Command Center</h1>
      <p className="text-neutral-400">
        Phase 0 foundations. Pipeline, Research, Studio, and Analytics views land in
        Phases 1–5.
      </p>
      <div className="flex flex-col gap-2">
        <Link href="/research" className="text-brand-orange underline">
          → Research Queue
        </Link>
        <Link href="/system" className="text-brand-orange underline">
          → System health
        </Link>
      </div>
    </div>
  );
}
