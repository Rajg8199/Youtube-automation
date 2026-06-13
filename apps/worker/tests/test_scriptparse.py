"""Pure parsing/timing tests for production (no ffmpeg/PIL needed)."""

from app.production.scriptparse import (
    allocate_durations,
    parse_scenes,
    split_segments,
    strip_scene_markers,
)


def test_strip_markers():
    assert "[SCENE" not in strip_scene_markers("[SCENE: spec-card] hello [SCENE: chart] world")


def test_split_segments_on_danda_and_period():
    segs = split_segments("Pehla vakya hai। Doosra sentence. Teesra!")
    assert len(segs) == 3


def test_split_segments_strips_markers():
    segs = split_segments("[SCENE: intro] Sirf yahi bolna hai.")
    assert segs == ["Sirf yahi bolna hai."]


def test_split_long_sentence_wraps():
    long = "word " * 100  # ~500 chars, no sentence enders
    segs = split_segments(long.strip(), max_len=240)
    assert len(segs) >= 2
    assert all(len(s) <= 240 for s in segs)


def test_parse_scenes_builds_hook_plus_markers():
    scenes = parse_scenes("Hook line", "[SCENE: price-tracker] price text [SCENE: chart] chart text")
    assert scenes[0].template == "intro"
    assert scenes[0].text == "Hook line"
    assert scenes[1].template == "price-tracker"
    assert scenes[2].template == "chart"


def test_parse_scenes_unknown_template_falls_back():
    scenes = parse_scenes("Hook", "[SCENE: made-up-thing foo] body")
    body_scene = scenes[-1]
    assert body_scene.template == "talking-points"
    assert "foo" in body_scene.caption  # remainder kept as caption


def test_parse_scenes_no_markers():
    scenes = parse_scenes("Hook", "just some narration with no markers")
    assert len(scenes) == 2
    assert scenes[1].template == "talking-points"


def test_allocate_durations_sums_close_to_total():
    scenes = parse_scenes("Short hook", "[SCENE: chart] a longer body segment here for weighting")
    durs = allocate_durations(scenes, 30.0)
    assert len(durs) == len(scenes)
    assert all(d >= 2.0 for d in durs)
    assert abs(sum(durs) - 30.0) < len(scenes) * 2  # min-clamp may nudge the total
