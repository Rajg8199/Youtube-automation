import { NextRequest, NextResponse } from "next/server";
import { setAutonomy } from "@/lib/worker";

export async function POST(req: NextRequest) {
  const { gate, mode } = await req.json();
  const res = await setAutonomy(gate, mode);
  const body = await res.json().catch(() => ({}));
  return NextResponse.json(body, { status: res.status });
}
