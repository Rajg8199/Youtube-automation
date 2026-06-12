/**
 * STACK_TIER resolver: selects provider adapters by tier.
 * Phase 0 wires only mock adapters; real adapters (Sarvam/ElevenLabs/Remotion/YouTube)
 * land in later phases behind these same factories.
 */

import type { StackTier } from "@pwg/shared";
import { MockTTSProvider } from "./tts/mock.js";
import { MockResearchSource } from "./research/mock.js";
import { MockVideoRenderer } from "./video/mock.js";
import { MockPublisher } from "./publish/mock.js";
import type { TTSProvider } from "./tts/types.js";
import type { VideoRenderer } from "./video/types.js";
import type { Publisher } from "./publish/types.js";
import type { ResearchSource } from "./research/types.js";

export interface ProviderBundle {
  tier: StackTier;
  tts: TTSProvider;
  renderer: VideoRenderer;
  publisher: Publisher;
  research: ResearchSource;
}

/** budget -> cheap/free adapters; premium -> paid adapters. Mocks for now. */
export function resolveProviders(tier: StackTier): ProviderBundle {
  // When real adapters exist, switch here on `tier`.
  const ttsBillAs = tier === "premium" ? "elevenlabs" : "sarvam";
  return {
    tier,
    tts: new MockTTSProvider(ttsBillAs),
    renderer: new MockVideoRenderer(),
    publisher: new MockPublisher(),
    research: new MockResearchSource(),
  };
}
