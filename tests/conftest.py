"""Shared test fixtures."""
import pytest

import monoline.config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Keep tests off the user's real config file."""
    monkeypatch.setattr(monoline.config, "config_path",
                        lambda: tmp_path / "config.toml")
