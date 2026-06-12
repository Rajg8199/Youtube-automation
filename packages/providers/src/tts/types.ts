/** TTS provider abstraction. Handles Hinglish code-switching across adapters. */

export interface TTSSegment {
  /** Text to speak (may mix Devanagari + Latin tech terms). */
  text: string;
  /** Optional voice id / preset specific to the provider. */
  voice?: string;
}

export interface TTSResult {
  /** Path to the generated audio in storage (or local in dev). */
  audioPath: string;
  durationSec: number;
  /** Word-level timestamps for subtitle + scene sync (later phases populate fully). */
  wordTimestamps: { word: string; startSec: number; endSec: number }[];
  costUsd: number;
  provider: string;
}

export interface TTSProvider {
  readonly name: string;
  /** Approx chars this provider can bill; used by the cost calculator. */
  synthesize(segment: TTSSegment): Promise<TTSResult>;
}
