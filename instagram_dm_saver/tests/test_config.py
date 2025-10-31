"""Tests for configuration management."""

import pytest
from pathlib import Path

from instagram_dm_saver.storage import AppConfig
from instagram_dm_saver.utils.exceptions import ConfigurationError


def test_config_creation(temp_config_dir):
    """Test config creation with default values."""
    config = AppConfig(config_dir=temp_config_dir)

    assert config.config_dir == temp_config_dir
    assert config.credential_storage == "keyring"
    assert config.default_message_count == 1000
    assert config.batch_size == 20


def test_config_directories_created(temp_config_dir):
    """Test that directories are created automatically."""
    config = AppConfig(
        config_dir=temp_config_dir / "config",
        save_dir=temp_config_dir / "saved",
    )

    assert config.config_dir.exists()
    assert config.save_dir.exists()


def test_config_save_and_load(temp_config_dir):
    """Test saving and loading configuration."""
    # Create and save config
    config1 = AppConfig(
        config_dir=temp_config_dir,
        default_message_count=500,
        credential_storage="file",
    )
    config1.save()

    # Load config
    config2 = AppConfig.load(temp_config_dir / "config.json")

    assert config2.default_message_count == 500
    assert config2.credential_storage == "file"


def test_config_validation():
    """Test configuration validation."""
    with pytest.raises(ValueError):
        # Invalid message count (too high)
        AppConfig(default_message_count=20000)

    with pytest.raises(ValueError):
        # Invalid batch size (too low)
        AppConfig(batch_size=1)


def test_config_get_paths(test_config):
    """Test getting file paths from config."""
    session_file = test_config.get_session_file()
    creds_file = test_config.get_credentials_file()

    assert session_file.parent == test_config.config_dir
    assert creds_file.parent == test_config.config_dir
    assert session_file.name == "session.json"
    assert creds_file.name == "credentials.enc"
