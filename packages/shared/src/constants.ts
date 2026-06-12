/** Shared constants: timezone, currency, Claude model ids. */

export const IST_TZ = "Asia/Kolkata";
export const CURRENCY = "INR";

/** Claude model ids (Jan 2026). */
export const MODELS = {
  haiku: "claude-haiku-4-5-20251001",
  sonnet: "claude-sonnet-4-6",
  opus: "claude-opus-4-8",
} as const;

export type ModelId = (typeof MODELS)[keyof typeof MODELS];

export type StackTier = "budget" | "premium";

/** Operating-economics targets (USD) from the master spec §13. */
export const COST_TARGETS = {
  perLongVideoMax: 1.0,
  monthlyMax: 50.0,
} as const;

/** Format USD as ₹ for the dashboard (approx; live FX wired later). */
export const USD_TO_INR_FALLBACK = 84;
