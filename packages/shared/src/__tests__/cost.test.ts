import { describe, it, expect } from "vitest";
import { llmCostUsd, ttsCostUsd } from "../cost.js";
import { MODELS } from "../constants.js";

describe("llmCostUsd", () => {
  it("prices Sonnet input+output correctly", () => {
    expect(llmCostUsd(MODELS.sonnet, 1000, 500)).toBeCloseTo(0.003 + 0.0075, 12);
  });
  it("is zero at zero tokens", () => {
    expect(llmCostUsd(MODELS.haiku, 0, 0)).toBe(0);
  });
  it("throws on unknown model", () => {
    expect(() => llmCostUsd("gpt-nope", 1, 1)).toThrow();
  });
});

describe("ttsCostUsd", () => {
  it("edge is free", () => {
    expect(ttsCostUsd("edge", 5000)).toBe(0);
  });
  it("sarvam charges per 1k chars", () => {
    expect(ttsCostUsd("sarvam", 2000)).toBeCloseTo(0.03, 12);
  });
  it("throws on unknown provider", () => {
    expect(() => ttsCostUsd("nope", 100)).toThrow();
  });
});
