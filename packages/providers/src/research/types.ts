/** Research source abstraction: RSS / Reddit / API feeds → raw signals. */

export interface RawSignalInput {
  externalId: string;
  title: string;
  url?: string;
  content?: string;
  publishedAt?: string; // ISO
}

export interface ResearchSource {
  readonly name: string;
  readonly type: "rss" | "reddit" | "api" | "scrape";
  /** Pull the latest items from this source. */
  poll(): Promise<RawSignalInput[]>;
}
