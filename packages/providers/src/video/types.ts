/** Video renderer abstraction (primary: Remotion). Optional gen-video plugin. */

export interface RenderRequest {
  contentItemId: string;
  /** Scene plan props the renderer consumes (Remotion composition input). */
  scenes: unknown[];
  voiceoverPath?: string;
  aspect: "16:9" | "9:16";
}

export interface RenderResult {
  videoPath: string;
  durationSec: number;
  costUsd: number;
  renderer: string;
}

export interface VideoRenderer {
  readonly name: string;
  render(req: RenderRequest): Promise<RenderResult>;
}

/** Optional generative-video plugin (Kling/Runway/Veo) behind a cost cap. */
export interface GenerativeVideoPlugin {
  readonly name: string;
  readonly costCapUsd: number;
  generateClip(prompt: string, seconds: number): Promise<RenderResult>;
}
