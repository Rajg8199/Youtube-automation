import { describe, it, expect } from "vitest";
import { resolveProviders } from "../resolver.js";

describe("resolveProviders", () => {
  it("budget tier bills TTS as sarvam and renders at zero cost", async () => {
    const b = resolveProviders("budget");
    expect(b.tier).toBe("budget");
    const tts = await b.tts.synthesize({ text: "नमस्ते Galaxy S26 review" });
    expect(tts.costUsd).toBeGreaterThan(0);
    const render = await b.renderer.render({
      contentItemId: "x",
      scenes: [1, 2, 3],
      aspect: "16:9",
    });
    expect(render.costUsd).toBe(0);
  });

  it("premium tier produces a manual kit publisher by default", async () => {
    const b = resolveProviders("premium");
    const res = await b.publisher.publish({
      contentItemId: "x",
      videoPath: "v.mp4",
      title: "t",
      description: "d",
      tags: [],
      thumbnailPath: "th.png",
      syntheticMediaDisclosure: true,
    });
    expect(res.method).toBe("manual_kit");
    expect(res.quotaCost).toBe(0);
  });
});
