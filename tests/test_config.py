from pathlib import Path

from monoline.config import Config, load_config


def test_first_run_writes_defaults(tmp_path: Path):
    p = tmp_path / "config.toml"
    cfg = load_config(p)
    assert p.exists()
    assert cfg == Config()


def test_reads_values(tmp_path: Path):
    p = tmp_path / "config.toml"
    p.write_text('shape_correct = "always"\npalette = "nord"\nsmoothing = 0.8\n')
    cfg = load_config(p)
    assert (cfg.shape_correct, cfg.palette, cfg.smoothing) == ("always", "nord", 0.8)


def test_invalid_values_fall_back(tmp_path: Path):
    p = tmp_path / "config.toml"
    p.write_text('shape_correct = "sometimes"\nsmoothing = 9.0\n')
    cfg = load_config(p)
    assert cfg.shape_correct == "ctrl"
    assert cfg.smoothing == 0.5


def test_unparseable_file_falls_back(tmp_path: Path):
    p = tmp_path / "config.toml"
    p.write_text("not [valid toml ===")
    assert load_config(p) == Config()
