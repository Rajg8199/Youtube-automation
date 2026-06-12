/** Mock research source returning a fixed signal set. */

import type { RawSignalInput, ResearchSource } from "./types.js";

export class MockResearchSource implements ResearchSource {
  readonly type = "rss" as const;

  constructor(
    readonly name = "mock:rss",
    private readonly items: RawSignalInput[] = [
      {
        externalId: "mock-1",
        title: "Samsung Galaxy S26 Ultra leaked specs surface",
        url: "https://example.com/s26",
        publishedAt: new Date().toISOString(),
      },
    ],
  ) {}

  async poll(): Promise<RawSignalInput[]> {
    return this.items;
  }
}
