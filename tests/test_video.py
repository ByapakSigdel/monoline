import pytest
from PIL import Image

from monoline.video import VideoPlayer, is_animated_gif, is_video_path


@pytest.fixture
def anim_gif(tmp_path):
    p = tmp_path / "anim.gif"
    frames = [
        Image.new("RGB", (20, 20), (255, 0, 0)),
        Image.new("RGB", (20, 20), (0, 255, 0)),
        Image.new("RGB", (20, 20), (0, 0, 255)),
    ]
    frames[0].save(p, save_all=True, append_images=frames[1:],
                   duration=100, loop=0)
    return str(p)


@pytest.fixture
def static_gif(tmp_path):
    p = tmp_path / "still.gif"
    Image.new("RGB", (10, 10), (128, 128, 128)).save(p)
    return str(p)


def test_is_animated_gif(anim_gif, static_gif):
    assert is_animated_gif(anim_gif) is True
    assert is_animated_gif(static_gif) is False


def test_is_video_path(anim_gif, static_gif):
    assert is_video_path(anim_gif) is True
    assert is_video_path(static_gif) is False
    assert is_video_path("clip.mp4") is True


def test_video_player_reads_frames(anim_gif):
    player = VideoPlayer(anim_gif, 40, 40, "#1a1b26")
    assert player.fps >= 1.0
    first = player.next_bitmap()
    second = player.next_bitmap()
    assert first.width == 40 and first.height == 40
    assert first.cells != second.cells


def test_video_player_loops(anim_gif):
    player = VideoPlayer(anim_gif, 40, 40, "#1a1b26")
    seen = [player.next_bitmap().cells for _ in range(4)]
    assert seen[0] == seen[3]
