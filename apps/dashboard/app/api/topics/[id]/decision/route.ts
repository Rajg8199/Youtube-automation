import { NextRequest, NextResponse } from "next/server";
import { decideTopic } from "@/lib/worker";

// Proxy the greenlight/reject decision to the worker (server-side, no CORS).
export async function POST(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  const { action } = await req.json();
  if (action !== "greenlight" && action !== "reject") {
    return NextResponse.json({ error: "invalid action" }, { status: 400 });
  }
  const res = await decideTopic(params.id, action);
  const body = await res.json().catch(() => ({}));
  return NextResponse.json(body, { status: res.status });
}
