"""Secure credential storage with multiple backend support."""

import json
import os
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

from ..utils.exceptions import CredentialError
from ..utils.logger import get_logger

logger = get_logger(__name__)

KEYRING_SERVICE = "instagram_dm_fetcher"


class CredentialManager:
    """
    Manage Instagram credentials with multiple storage backends.

    Supports:
    - System keyring (most secure)
    - Encrypted file storage
    - Environment variables
    - No storage (always prompt)
    """

    def __init__(self, storage_method: str = "keyring"):
        """
        Initialize credential manager.

        Args:
            storage_method: Storage method (keyring, file, env, none)
        """
        self.storage_method = storage_method
        self._cipher: Optional[Fernet] = None

        if storage_method == "keyring" and not KEYRING_AVAILABLE:
            logger.warning("Keyring not available, falling back to file storage")
            self.storage_method = "file"

    def _get_cipher(self) -> Fernet:
        """Get or create Fernet cipher for encryption."""
        if self._cipher is not None:
            return self._cipher

        # Try to get encryption key from keyring
        if KEYRING_AVAILABLE:
            try:
                key_str = keyring.get_password(KEYRING_SERVICE, "encryption_key")
                if key_str:
                    self._cipher = Fernet(key_str.encode())
                    return self._cipher
            except Exception as e:
                logger.debug(f"Could not retrieve encryption key from keyring: {e}")

        # Generate new key
        key = Fernet.generate_key()

        # Try to save to keyring
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(KEYRING_SERVICE, "encryption_key", key.decode())
                logger.info("Encryption key saved to system keyring")
            except Exception as e:
                logger.warning(f"Could not save encryption key to keyring: {e}")

        self._cipher = Fernet(key)
        return self._cipher

    def save_credentials(
        self,
        username: str,
        password: str,
        file_path: Optional[Path] = None
    ) -> bool:
        """
        Save credentials using configured storage method.

        Args:
            username: Instagram username
            password: Instagram password
            file_path: Path for file storage (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.storage_method == "keyring":
                return self._save_to_keyring(username, password)
            elif self.storage_method == "file":
                return self._save_to_file(username, password, file_path)
            elif self.storage_method == "env":
                logger.info("Set IG_USERNAME and IG_PASSWORD environment variables")
                return True
            else:  # none
                logger.info("Credentials will not be saved")
                return True

        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise CredentialError(f"Failed to save credentials: {e}")

    def load_credentials(
        self,
        file_path: Optional[Path] = None
    ) -> Optional[Dict[str, str]]:
        """
        Load credentials using configured storage method.

        Args:
            file_path: Path for file storage (optional)

        Returns:
            Dict with username and password, or None if not found
        """
        try:
            # First check environment variables
            username = os.getenv("IG_USERNAME")
            password = os.getenv("IG_PASSWORD")
            if username and password:
                logger.info("Loaded credentials from environment variables")
                return {"username": username, "password": password}

            # Try configured storage method
            if self.storage_method == "keyring":
                return self._load_from_keyring()
            elif self.storage_method == "file":
                return self._load_from_file(file_path)
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def delete_credentials(
        self,
        username: Optional[str] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """
        Delete saved credentials.

        Args:
            username: Username (required for keyring)
            file_path: Path for file storage (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.storage_method == "keyring":
                if not username:
                    logger.error("Username required to delete keyring credentials")
                    return False
                return self._delete_from_keyring(username)
            elif self.storage_method == "file":
                return self._delete_from_file(file_path)
            else:
                return True

        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False

    # Keyring methods
    def _save_to_keyring(self, username: str, password: str) -> bool:
        """Save credentials to system keyring."""
        if not KEYRING_AVAILABLE:
            raise CredentialError("Keyring not available")

        try:
            keyring.set_password(KEYRING_SERVICE, username, password)
            # Also save username reference
            keyring.set_password(KEYRING_SERVICE, "last_username", username)
            logger.info(f"Credentials saved to keyring for {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to save to keyring: {e}")
            raise CredentialError(f"Failed to save to keyring: {e}")

    def _load_from_keyring(self) -> Optional[Dict[str, str]]:
        """Load credentials from system keyring."""
        if not KEYRING_AVAILABLE:
            return None

        try:
            # Get last used username
            username = keyring.get_password(KEYRING_SERVICE, "last_username")
            if not username:
                return None

            password = keyring.get_password(KEYRING_SERVICE, username)
            if password:
                logger.info(f"Loaded credentials from keyring for {username}")
                return {"username": username, "password": password}
            return None

        except Exception as e:
            logger.error(f"Failed to load from keyring: {e}")
            return None

    def _delete_from_keyring(self, username: str) -> bool:
        """Delete credentials from system keyring."""
        if not KEYRING_AVAILABLE:
            return False

        try:
            keyring.delete_password(KEYRING_SERVICE, username)
            # Clear last username if it matches
            last_username = keyring.get_password(KEYRING_SERVICE, "last_username")
            if last_username == username:
                keyring.delete_password(KEYRING_SERVICE, "last_username")
            logger.info(f"Credentials deleted from keyring for {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from keyring: {e}")
            return False

    # File methods with encryption
    def _save_to_file(
        self,
        username: str,
        password: str,
        file_path: Optional[Path] = None
    ) -> bool:
        """Save encrypted credentials to file."""
        if file_path is None:
            from .config import get_config
            file_path = get_config().get_credentials_file()

        try:
            cipher = self._get_cipher()
            data = json.dumps({"username": username, "password": password})
            encrypted = cipher.encrypt(data.encode())

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(encrypted)

            logger.info(f"Encrypted credentials saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save to file: {e}")
            raise CredentialError(f"Failed to save to file: {e}")

    def _load_from_file(self, file_path: Optional[Path] = None) -> Optional[Dict[str, str]]:
        """Load encrypted credentials from file."""
        if file_path is None:
            from .config import get_config
            file_path = get_config().get_credentials_file()

        if not file_path.exists():
            return None

        try:
            cipher = self._get_cipher()
            encrypted = file_path.read_bytes()
            decrypted = cipher.decrypt(encrypted)
            data = json.loads(decrypted.decode())

            logger.info(f"Loaded credentials from {file_path}")
            return data

        except Exception as e:
            logger.error(f"Failed to load from file: {e}")
            return None

    def _delete_from_file(self, file_path: Optional[Path] = None) -> bool:
        """Delete credentials file."""
        if file_path is None:
            from .config import get_config
            file_path = get_config().get_credentials_file()

        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted credentials file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
