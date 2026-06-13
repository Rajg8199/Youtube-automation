import { NextRequest, NextResponse } from "next/server";
import { decideScript } from "@/lib/worker";

// Proxy the script-gate decision to the worker (server-side, no CORS).
export async function POST(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  const { action, note } = await req.json();
  if (!["approve", "request_changes", "reject"].includes(action)) {
    return NextResponse.json({ error: "invalid action" }, { status: 400 });
  }
  const res = await decideScript(params.id, action, note);
  const body = await res.json().catch(() => ({}));
  return NextResponse.json(body, { status: res.status });
}
