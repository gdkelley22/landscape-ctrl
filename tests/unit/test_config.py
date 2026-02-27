"""
Unit tests for configuration management (config.py).
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from landscape_ctrl.config import LandscapeConfig, save_config, load_config


class TestLandscapeConfig:
    def test_url_trailing_slash_stripped(self):
        cfg = LandscapeConfig(url="https://landscape.example.com/")
        assert cfg.url == "https://landscape.example.com"

    def test_base_url_v2(self):
        cfg = LandscapeConfig(url="https://landscape.example.com", api_version="v2")
        assert cfg.base_url == "https://landscape.example.com/api/v2"

    def test_base_url_legacy(self):
        cfg = LandscapeConfig(url="https://landscape.example.com", api_version="legacy")
        assert cfg.base_url == "https://landscape.example.com/api"

    def test_legacy_url_always_legacy(self):
        cfg = LandscapeConfig(url="https://landscape.example.com", api_version="v2")
        assert cfg.legacy_url == "https://landscape.example.com/api"

    def test_ssl_context_default(self):
        cfg = LandscapeConfig(url="https://x.com")
        assert cfg.ssl_context() is True

    def test_ssl_context_no_verify(self):
        cfg = LandscapeConfig(url="https://x.com", verify_ssl=False)
        assert cfg.ssl_context() is False

    def test_ssl_context_custom_ca(self):
        cfg = LandscapeConfig(url="https://x.com", ssl_ca_file="/etc/ssl/ca.pem")
        assert cfg.ssl_context() == "/etc/ssl/ca.pem"


class TestSaveLoadConfig:
    def test_roundtrip(self, tmp_path):
        """Save config and load it back — values should match."""
        cfg = LandscapeConfig(
            url="https://ls.example.com",
            account="myorg",
            api_version="legacy",
            access_key="MYKEY",
        )

        config_file = tmp_path / "config.toml"
        data_dir = tmp_path / "data"

        with (
            patch("landscape_ctrl.config.CONFIG_DIR", tmp_path),
            patch("landscape_ctrl.config.CONFIG_FILE", config_file),
            patch("landscape_ctrl.config.DATA_DIR", data_dir),
        ):
            save_config(cfg)
            assert config_file.exists()

            loaded = load_config()
            assert loaded.url == "https://ls.example.com"
            assert loaded.account == "myorg"
            assert loaded.api_version == "legacy"
            assert loaded.access_key == "MYKEY"

    def test_load_missing_raises(self, tmp_path):
        config_file = tmp_path / "nonexistent.toml"
        with patch("landscape_ctrl.config.CONFIG_FILE", config_file):
            with pytest.raises(FileNotFoundError):
                load_config()
