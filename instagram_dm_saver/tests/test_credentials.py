"""Tests for credential management."""

import pytest
from pathlib import Path

from instagram_dm_saver.storage import CredentialManager
from instagram_dm_saver.utils.exceptions import CredentialError


def test_credential_manager_creation():
    """Test creating credential manager."""
    manager = CredentialManager(storage_method="file")
    assert manager.storage_method == "file"


def test_save_and_load_file_credentials(temp_config_dir):
    """Test saving and loading credentials to encrypted file."""
    manager = CredentialManager(storage_method="file")
    creds_file = temp_config_dir / "credentials.enc"

    # Save credentials
    success = manager.save_credentials("test_user", "test_pass", creds_file)
    assert success
    assert creds_file.exists()

    # Load credentials
    loaded = manager.load_credentials(creds_file)
    assert loaded is not None
    assert loaded["username"] == "test_user"
    assert loaded["password"] == "test_pass"


def test_delete_file_credentials(temp_config_dir):
    """Test deleting credentials file."""
    manager = CredentialManager(storage_method="file")
    creds_file = temp_config_dir / "credentials.enc"

    # Save and delete
    manager.save_credentials("test_user", "test_pass", creds_file)
    assert creds_file.exists()

    manager.delete_credentials(file_path=creds_file)
    assert not creds_file.exists()


def test_load_nonexistent_credentials(temp_config_dir):
    """Test loading credentials when file doesn't exist."""
    manager = CredentialManager(storage_method="file")
    creds_file = temp_config_dir / "nonexistent.enc"

    loaded = manager.load_credentials(creds_file)
    assert loaded is None


def test_credential_encryption(temp_config_dir):
    """Test that credentials are encrypted in file."""
    manager = CredentialManager(storage_method="file")
    creds_file = temp_config_dir / "credentials.enc"

    manager.save_credentials("test_user", "secret_password", creds_file)

    # Read raw file content
    raw_content = creds_file.read_bytes()

    # Should not contain plaintext password
    assert b"secret_password" not in raw_content
    assert b"test_user" not in raw_content


def test_storage_method_none():
    """Test 'none' storage method."""
    manager = CredentialManager(storage_method="none")

    # Should succeed but not actually save
    success = manager.save_credentials("test", "test")
    assert success

    # Should return None
    loaded = manager.load_credentials()
    assert loaded is None
