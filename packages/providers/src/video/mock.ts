/** Mock renderer — returns a fake path, zero cost (self-hosted render). */

import type { RenderRequest, RenderResult, VideoRenderer } from "./types.js";

export class MockVideoRenderer implements VideoRenderer {
  readonly name = "mock:remotion";

  async render(req: RenderRequest): Promise<RenderResult> {
    return {
      videoPath: `mock://render/${req.contentItemId}-${req.aspect.replace(":", "x")}.mp4`,
      durationSec: req.scenes.length * 5,
      costUsd: 0,
      renderer: this.name,
    };
  }
}
