/**
 * Cost calculator — mirrors apps/worker/app/costs.py.
 * Keep MODEL_PRICING and TTS_PRICING in sync across both runtimes (ADR-0006).
 */

import { MODELS } from "./constants.js";

/** USD per 1M tokens: [input, output]. */
export const MODEL_PRICING: Record<string, [number, number]> = {
  [MODELS.haiku]: [1.0, 5.0],
  [MODELS.sonnet]: [3.0, 15.0],
  [MODELS.opus]: [5.0, 25.0],
};

/** USD per 1k characters. */
export const TTS_PRICING_PER_1K_CHARS: Record<string, number> = {
  sarvam: 0.015,
  elevenlabs: 0.3,
  google: 0.016,
  edge: 0.0,
};

export function llmCostUsd(
  model: string,
  inputTokens: number,
  outputTokens: number,
): number {
  const pricing = MODEL_PRICING[model];
  if (!pricing) throw new Error(`unknown model for pricing: ${model}`);
  const [inRate, outRate] = pricing;
  return (inputTokens / 1_000_000) * inRate + (outputTokens / 1_000_000) * outRate;
}

export function ttsCostUsd(provider: string, chars: number): number {
  const rate = TTS_PRICING_PER_1K_CHARS[provider];
  if (rate === undefined) throw new Error(`unknown TTS provider for pricing: ${provider}`);
  return (chars / 1000) * rate;
}

export type CostCategory =
  | "llm"
  | "tts"
  | "video_gen"
  | "render"
  | "storage"
  | "api"
  | "infra";
