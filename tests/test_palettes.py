import re

from monoline.palettes import PALETTES, get_palette

HEX = re.compile(r"^#[0-9a-f]{6}$")


def test_seven_palettes_nine_colors():
    assert [p.name for p in PALETTES] == [
        "tokyonight", "catppuccin", "gruvbox", "nord", "pastel", "neon", "mono"
    ]
    for p in PALETTES:
        assert len(p.colors) == 9
        for c in (p.background, p.grid) + p.colors:
            assert HEX.match(c), (p.name, c)


def test_get_palette_fallback():
    assert get_palette("tokyonight").name == "tokyonight"
    assert get_palette("nonsense").name == "tokyonight"
