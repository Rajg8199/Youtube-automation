import { describe, it, expect } from "vitest";
import {
  CONTENT_STATUSES,
  canTransition,
  assertTransition,
  isTerminal,
  nextStatuses,
  type ContentStatus,
} from "../state-machine.js";

describe("state machine", () => {
  it("has 19 statuses", () => {
    expect(CONTENT_STATUSES).toHaveLength(19);
  });

  it("allows the happy path end to end", () => {
    const path: ContentStatus[] = [
      "idea",
      "researched",
      "scripting",
      "script_qa",
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
    ];
    for (let i = 0; i < path.length - 1; i++) {
      expect(canTransition(path[i]!, path[i + 1]!)).toBe(true);
    }
  });

  it("supports the QA revise loop", () => {
    expect(canTransition("script_qa", "qa_failed")).toBe(true);
    expect(canTransition("qa_failed", "scripting")).toBe(true);
  });

  it("rejects illegal jumps", () => {
    expect(canTransition("idea", "published")).toBe(false);
    expect(canTransition("idea", "idea")).toBe(false);
    expect(() => assertTransition("idea", "published")).toThrow();
  });

  it("allows failure from processing states only", () => {
    expect(canTransition("publishing", "failed")).toBe(true);
    expect(canTransition("idea", "failed")).toBe(false);
  });

  it("marks terminal states", () => {
    expect(isTerminal("archived")).toBe(true);
    expect(isTerminal("rejected")).toBe(true);
    expect(isTerminal("idea")).toBe(false);
    expect(nextStatuses("archived")).toHaveLength(0);
  });
});
