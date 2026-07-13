from monoline.bitmap import Bitmap
from monoline.document import Stroke
from monoline.reveal import (
    STYLES,
    RevealPlayer,
    build_frames,
    snapshot_bitmap,
)


def test_snapshot_merges_strokes_and_bitmap():
    bm = Bitmap(8, 8, {(2, 1): (0x01, "#111111")})
    stroke = Stroke(points=[(0.0, 0.0)], color="#ff0000")
    snap = snapshot_bitmap([stroke], 8, 8, bitmap=bm)
    assert snap is not None
    assert (0, 0) in snap.cells
    assert (2, 1) in snap.cells


def test_snapshot_empty_returns_none():
    assert snapshot_bitmap([], 8, 8) is None


def test_build_frames_all_styles():
    final = Bitmap(16, 16, {
        (0, 0): (0x01, "#a"),
        (1, 0): (0x02, "#b"),
        (0, 1): (0x04, "#c"),
        (3, 2): (0x08, "#d"),
    })
    for style in STYLES:
        frames = build_frames(final, style)
        assert len(frames) >= 2
        assert frames[0].cells != final.cells or style == "pop"
        assert frames[-1].cells == final.cells


def test_drop_animation_reaches_final():
    final = Bitmap(8, 16, {(1, 3): (0xFF, "#fff")})
    frames = build_frames(final, "drop")
    assert frames[-1].cells == final.cells
    assert any(frames[i].cells != final.cells for i in range(len(frames) - 1))


def test_reveal_player_steps_and_finishes():
    final = Bitmap(8, 8, {(0, 0): (0x01, "#a")})
    frames = build_frames(final, "scan_down", min_frames=4, max_frames=8)
    player = RevealPlayer(frames, fps=12.0)
    seen = []
    while True:
        bm = player.next_bitmap()
        if bm is None:
            break
        seen.append(bm)
    assert len(seen) == len(frames)
    assert player.done


def test_unknown_style_raises():
    final = Bitmap(8, 8, {(0, 0): (0x01, "#a")})
    try:
        build_frames(final, "nope")
    except ValueError as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("expected ValueError")
