import { NextRequest, NextResponse } from "next/server";
import { decidePublish } from "@/lib/worker";

// Proxy the publish-gate decision to the worker (server-side, no CORS).
export async function POST(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  const { action } = await req.json();
  if (!["approve", "reject"].includes(action)) {
    return NextResponse.json({ error: "invalid action" }, { status: 400 });
  }
  const res = await decidePublish(params.id, action);
  const body = await res.json().catch(() => ({}));
  return NextResponse.json(body, { status: res.status });
}
