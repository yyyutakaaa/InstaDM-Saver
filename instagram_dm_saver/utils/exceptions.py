"""Custom exceptions for Instagram DM Fetcher."""


class InstagramDMError(Exception):
    """Base exception for all Instagram DM operations."""
    pass


class AuthenticationError(InstagramDMError):
    """Raised when authentication fails."""
    pass


class TwoFactorRequired(AuthenticationError):
    """Raised when 2FA verification is required."""
    pass


class MessageFetchError(InstagramDMError):
    """Raised when message fetching fails."""
    pass


class MediaValidationError(InstagramDMError):
    """Raised when media validation fails."""
    pass


class ConversationError(InstagramDMError):
    """Raised when conversation operations fail."""
    pass


class StorageError(InstagramDMError):
    """Raised when storage operations fail."""
    pass


class ConfigurationError(InstagramDMError):
    """Raised when configuration is invalid."""
    pass


class RateLimitError(InstagramDMError):
    """Raised when rate limit is exceeded."""
    pass


class CredentialError(InstagramDMError):
    """Raised when credential operations fail."""
    pass


class ExportError(InstagramDMError):
    """Raised when export operations fail."""
    pass
