/** Publisher abstraction: YouTube Data API upload or a manual publish-kit fallback. */

export interface PublishRequest {
  contentItemId: string;
  videoPath: string;
  title: string;
  description: string;
  tags: string[];
  thumbnailPath: string;
  scheduledAt?: string; // ISO
  syntheticMediaDisclosure: boolean;
}

export interface PublishResult {
  method: "api" | "manual_kit";
  youtubeVideoId?: string;
  quotaCost: number;
  /** For manual_kit: a path/bundle the dashboard exposes for one-click publish. */
  kitPath?: string;
}

export interface Publisher {
  readonly name: string;
  /** API publishers must check the quota ledger before consuming units. */
  publish(req: PublishRequest): Promise<PublishResult>;
}
