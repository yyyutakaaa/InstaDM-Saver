"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

from instagrapi import Client
from instagrapi.types import DirectThread, DirectMessage, UserShort

from instagram_dm_saver.storage import AppConfig


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_config_dir):
    """Create test configuration."""
    config = AppConfig(
        config_dir=temp_config_dir / "config",
        save_dir=temp_config_dir / "saved_messages",
        log_dir=temp_config_dir / "logs",
        credential_storage="file",
        default_message_count=100,
    )
    return config


@pytest.fixture
def mock_client():
    """Create mock Instagram client."""
    client = Mock(spec=Client)
    client.user_id = 12345
    client.username = "test_user"
    return client


@pytest.fixture
def mock_user():
    """Create mock Instagram user."""
    user = Mock(spec=UserShort)
    user.pk = 67890
    user.username = "other_user"
    user.full_name = "Other User"
    return user


@pytest.fixture
def mock_thread(mock_user):
    """Create mock conversation thread."""
    thread = Mock(spec=DirectThread)
    thread.id = "thread_123"
    thread.users = [mock_user]
    thread.messages = []
    return thread


@pytest.fixture
def mock_message():
    """Create mock direct message."""
    from datetime import datetime

    message = Mock(spec=DirectMessage)
    message.id = "msg_123"
    message.user_id = 67890
    message.text = "Test message"
    message.timestamp = datetime.now()
    message.media = None
    return message


@pytest.fixture
def sample_messages(mock_message):
    """Create list of sample messages."""
    from datetime import datetime, timedelta
    import copy

    messages = []
    for i in range(10):
        msg = copy.deepcopy(mock_message)
        msg.id = f"msg_{i}"
        msg.text = f"Test message {i}"
        msg.timestamp = datetime.now() - timedelta(minutes=i)
        messages.append(msg)

    return messages
