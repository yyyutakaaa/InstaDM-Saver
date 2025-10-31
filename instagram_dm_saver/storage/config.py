"""Configuration management with validation."""

import json
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

from ..utils.exceptions import ConfigurationError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AppConfig(BaseModel):
    """Application configuration with validation."""

    # Directories
    config_dir: Path = Field(
        default=Path.home() / ".instagram_dm_fetcher",
        description="Directory for configuration files"
    )
    save_dir: Path = Field(
        default=Path.home() / "Instagram_DM_Fetcher_Chats",
        description="Directory for saved messages"
    )
    log_dir: Optional[Path] = Field(
        default=None,
        description="Directory for log files (defaults to config_dir/logs)"
    )

    # Credentials
    credential_storage: Literal["keyring", "file", "env", "none"] = Field(
        default="keyring",
        description="Method for storing credentials"
    )

    # Message fetching
    default_message_count: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Default number of messages to fetch"
    )
    batch_size: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Batch size for fetching messages"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of retries for failed operations"
    )

    # Rate limiting
    rate_limit_calls: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum API calls per time window"
    )
    rate_limit_window: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Rate limit time window in seconds"
    )

    # Export
    default_export_format: Literal["txt", "json", "csv"] = Field(
        default="txt",
        description="Default export format"
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        use_enum_values = True

    @field_validator("config_dir", "save_dir")
    @classmethod
    def create_directory(cls, v: Path) -> Path:
        """Create directory if it doesn't exist."""
        try:
            v.mkdir(parents=True, exist_ok=True)
            return v
        except Exception as e:
            raise ConfigurationError(f"Failed to create directory {v}: {e}")

    @field_validator("log_dir")
    @classmethod
    def set_log_dir_default(cls, v: Optional[Path], info) -> Path:
        """Set log_dir default based on config_dir."""
        if v is None:
            config_dir = info.data.get("config_dir", Path.home() / ".instagram_dm_fetcher")
            v = config_dir / "logs"
        try:
            v.mkdir(parents=True, exist_ok=True)
            return v
        except Exception as e:
            raise ConfigurationError(f"Failed to create log directory {v}: {e}")

    def save(self, config_file: Optional[Path] = None) -> None:
        """
        Save configuration to JSON file.

        Args:
            config_file: Path to config file. If None, uses config_dir/config.json
        """
        if config_file is None:
            config_file = self.config_dir / "config.json"

        try:
            # Convert Path objects to strings for JSON serialization
            config_dict = self.model_dump(mode='json')
            config_dict['config_dir'] = str(self.config_dir)
            config_dict['save_dir'] = str(self.save_dir)
            config_dict['log_dir'] = str(self.log_dir)

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)

            logger.info(f"Configuration saved to {config_file}")

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "AppConfig":
        """
        Load configuration from JSON file.

        Args:
            config_file: Path to config file. If None, uses default location

        Returns:
            AppConfig instance
        """
        if config_file is None:
            config_file = Path.home() / ".instagram_dm_fetcher" / "config.json"

        if not config_file.exists():
            logger.info("No config file found, using defaults")
            return cls()

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # Convert string paths back to Path objects
            if 'config_dir' in config_data:
                config_data['config_dir'] = Path(config_data['config_dir'])
            if 'save_dir' in config_data:
                config_data['save_dir'] = Path(config_data['save_dir'])
            if 'log_dir' in config_data and config_data['log_dir']:
                config_data['log_dir'] = Path(config_data['log_dir'])

            logger.info(f"Configuration loaded from {config_file}")
            return cls(**config_data)

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            logger.info("Using default configuration")
            return cls()

    def get_session_file(self) -> Path:
        """Get path to session file."""
        return self.config_dir / "session.json"

    def get_credentials_file(self) -> Path:
        """Get path to credentials file."""
        return self.config_dir / "credentials.enc"


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get global configuration instance.

    Returns:
        AppConfig instance
    """
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def reload_config() -> AppConfig:
    """
    Reload configuration from file.

    Returns:
        Fresh AppConfig instance
    """
    global _config
    _config = AppConfig.load()
    return _config
