"""
Instagram DM Saver - Fetch and save your Instagram direct messages.

A professional, modular tool for downloading Instagram DMs with support for
multiple export formats, secure credential storage, and robust error handling.
"""

__version__ = "2.0.0"
__author__ = "Instagram DM Saver Team"

from .core import InstagramAuthenticator, MessageManager
from .storage import AppConfig, get_config, CredentialManager, MessageExporter
from .utils import (
    InstagramDMError,
    AuthenticationError,
    MessageFetchError,
    ConversationError,
    get_logger,
    instagram_rate_limiter,
)

__all__ = [
    # Core
    "InstagramAuthenticator",
    "MessageManager",
    # Storage
    "AppConfig",
    "get_config",
    "CredentialManager",
    "MessageExporter",
    # Utils
    "InstagramDMError",
    "AuthenticationError",
    "MessageFetchError",
    "ConversationError",
    "get_logger",
    "instagram_rate_limiter",
    # Metadata
    "__version__",
    "__author__",
]
