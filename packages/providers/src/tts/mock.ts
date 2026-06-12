/** Mock TTS adapter — deterministic, no network. Used in Phase 0 tests + local dev. */

import { ttsCostUsd } from "@pwg/shared";
import type { TTSProvider, TTSResult, TTSSegment } from "./types.js";

export class MockTTSProvider implements TTSProvider {
  readonly name: string;

  constructor(private readonly billAs = "edge") {
    this.name = `mock:${billAs}`;
  }

  async synthesize(segment: TTSSegment): Promise<TTSResult> {
    const chars = segment.text.length;
    // ~15 chars/sec speaking rate as a rough estimate.
    const durationSec = Math.max(0.5, chars / 15);
    return {
      audioPath: `mock://tts/${encodeURIComponent(segment.text.slice(0, 16))}.wav`,
      durationSec,
      wordTimestamps: [],
      costUsd: ttsCostUsd(this.billAs, chars),
      provider: this.name,
    };
  }
}
