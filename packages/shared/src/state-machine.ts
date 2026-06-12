/**
 * content_items status state machine.
 * The 19 statuses match the DB CHECK constraint in 0003_pipeline.sql.
 * This module is the single source of truth for legal transitions.
 */

export const CONTENT_STATUSES = [
  "idea",
  "researched",
  "scripting",
  "script_qa",
  "qa_failed",
  "script_approved",
  "voiceover",
  "assembly",
  "thumbnail",
  "metadata",
  "ready_for_review",
  "approved",
  "scheduled",
  "publishing",
  "published",
  "analyzing",
  "archived",
  "rejected",
  "failed",
] as const;

export type ContentStatus = (typeof CONTENT_STATUSES)[number];

/** Terminal states: no outgoing transitions. */
export const TERMINAL_STATUSES: ReadonlySet<ContentStatus> = new Set([
  "archived",
  "rejected",
]);

/** Legal forward transitions. `failed` is reachable from any processing state (see canTransition). */
const TRANSITIONS: Record<ContentStatus, ContentStatus[]> = {
  idea: ["researched", "rejected"],
  researched: ["scripting", "rejected"],
  scripting: ["script_qa", "failed"],
  script_qa: ["script_approved", "qa_failed"],
  qa_failed: ["scripting", "rejected"], // revise loop or give up
  script_approved: ["voiceover"],
  voiceover: ["assembly", "failed"],
  assembly: ["thumbnail", "failed"],
  thumbnail: ["metadata", "failed"],
  metadata: ["ready_for_review"],
  ready_for_review: ["approved", "rejected"],
  approved: ["scheduled"],
  scheduled: ["publishing", "rejected"],
  publishing: ["published", "failed"],
  published: ["analyzing"],
  analyzing: ["archived"],
  archived: [],
  rejected: [],
  failed: ["scripting", "archived"], // manual recovery or retire
};

/** Processing states that may fail mid-flight even without an explicit edge. */
const FAILABLE: ReadonlySet<ContentStatus> = new Set([
  "researched",
  "scripting",
  "script_qa",
  "script_approved",
  "voiceover",
  "assembly",
  "thumbnail",
  "metadata",
  "scheduled",
  "publishing",
]);

export function canTransition(from: ContentStatus, to: ContentStatus): boolean {
  if (from === to) return false;
  if (to === "failed" && FAILABLE.has(from)) return true;
  return TRANSITIONS[from].includes(to);
}

export function nextStatuses(from: ContentStatus): ContentStatus[] {
  const base = new Set(TRANSITIONS[from]);
  if (FAILABLE.has(from)) base.add("failed");
  return [...base];
}

export function isTerminal(status: ContentStatus): boolean {
  return TERMINAL_STATUSES.has(status);
}

/** Throws if a transition is illegal — call before writing a pipeline_event. */
export function assertTransition(from: ContentStatus, to: ContentStatus): void {
  if (!canTransition(from, to)) {
    throw new Error(`illegal content_item transition: ${from} -> ${to}`);
  }
}
