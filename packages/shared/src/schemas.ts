/** Zod schemas shared across worker/agents/dashboard. Phase 0 covers the core enums. */

import { z } from "zod";
import { CONTENT_STATUSES } from "./state-machine.js";

export const ContentStatusSchema = z.enum(CONTENT_STATUSES);

export const FormatSchema = z.enum(["long", "short"]);

export const CategorySchema = z.enum([
  "launch",
  "leak",
  "comparison",
  "review",
  "buying_guide",
  "news",
  "ai_feature",
  "android_tips",
  "explainer",
]);

export const AutonomyGateSchema = z.enum(["script", "publish", "topic_selection"]);
export const AutonomyModeSchema = z.enum(["manual", "auto_with_veto", "full_auto"]);

export const CostCategorySchema = z.enum([
  "llm",
  "tts",
  "video_gen",
  "render",
  "storage",
  "api",
  "infra",
]);

/** A single verified fact in a research brief. */
export const FactSchema = z.object({
  claim: z.string(),
  value: z.string(),
  source_url: z.string().url(),
  confidence: z.number().min(0).max(1),
});

export type Fact = z.infer<typeof FactSchema>;
