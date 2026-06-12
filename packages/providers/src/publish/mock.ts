/** Mock publisher — always produces a manual kit (no quota consumed). */

import type { Publisher, PublishRequest, PublishResult } from "./types.js";

export class MockPublisher implements Publisher {
  readonly name = "mock:manual_kit";

  async publish(req: PublishRequest): Promise<PublishResult> {
    return {
      method: "manual_kit",
      quotaCost: 0,
      kitPath: `mock://kit/${req.contentItemId}.zip`,
    };
  }
}
