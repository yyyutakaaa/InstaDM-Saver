"""Tests for message exporters."""

import pytest
import json
import csv
from pathlib import Path

from instagram_dm_saver.storage import MessageExporter


def test_exporter_creation(temp_config_dir):
    """Test creating message exporter."""
    exporter = MessageExporter(temp_config_dir)
    assert exporter.save_dir == temp_config_dir
    assert exporter.save_dir.exists()


def test_sanitize_filename(temp_config_dir):
    """Test filename sanitization."""
    exporter = MessageExporter(temp_config_dir)

    # Test various problematic characters
    sanitized = exporter._sanitize_filename('user/with\\bad:chars|test')
    assert '/' not in sanitized
    assert '\\' not in sanitized
    assert ':' not in sanitized
    assert '|' not in sanitized


def test_export_txt(temp_config_dir, mock_thread, sample_messages, mock_client):
    """Test exporting messages to TXT format."""
    exporter = MessageExporter(temp_config_dir)

    output_path = exporter.export(
        mock_thread,
        sample_messages,
        format="txt",
        current_user_id=mock_client.user_id,
        current_username=mock_client.username
    )

    assert output_path.exists()
    assert output_path.suffix == ".txt"

    # Check content
    content = output_path.read_text(encoding='utf-8')
    assert "Conversation with" in content
    assert "Test message" in content


def test_export_json(temp_config_dir, mock_thread, sample_messages, mock_client):
    """Test exporting messages to JSON format."""
    exporter = MessageExporter(temp_config_dir)

    output_path = exporter.export(
        mock_thread,
        sample_messages,
        format="json",
        current_user_id=mock_client.user_id,
        current_username=mock_client.username
    )

    assert output_path.exists()
    assert output_path.suffix == ".json"

    # Parse and check JSON
    with open(output_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert "conversation_info" in data
    assert "messages" in data
    assert len(data["messages"]) == len(sample_messages)
    assert data["messages"][0]["text"] is not None


def test_export_csv(temp_config_dir, mock_thread, sample_messages, mock_client):
    """Test exporting messages to CSV format."""
    exporter = MessageExporter(temp_config_dir)

    output_path = exporter.export(
        mock_thread,
        sample_messages,
        format="csv",
        current_user_id=mock_client.user_id,
        current_username=mock_client.username
    )

    assert output_path.exists()
    assert output_path.suffix == ".csv"

    # Parse and check CSV
    with open(output_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == len(sample_messages)
    assert "Timestamp" in reader.fieldnames
    assert "Sender" in reader.fieldnames
    assert "Message" in reader.fieldnames


def test_export_creates_user_folder(temp_config_dir, mock_thread, sample_messages, mock_client):
    """Test that export creates user-specific folder."""
    exporter = MessageExporter(temp_config_dir)

    output_path = exporter.export(
        mock_thread,
        sample_messages,
        format="txt",
        current_user_id=mock_client.user_id
    )

    # Should be in a user-specific subfolder
    assert output_path.parent != temp_config_dir
    assert output_path.parent.name == mock_thread.users[0].username


def test_export_unsupported_format(temp_config_dir, mock_thread, sample_messages, mock_client):
    """Test error handling for unsupported format."""
    from instagram_dm_saver.utils.exceptions import ExportError

    exporter = MessageExporter(temp_config_dir)

    with pytest.raises(ExportError):
        exporter.export(
            mock_thread,
            sample_messages,
            format="xml",  # Unsupported
            current_user_id=mock_client.user_id
        )


def test_export_empty_messages(temp_config_dir, mock_thread, mock_client):
    """Test exporting with no messages."""
    exporter = MessageExporter(temp_config_dir)

    output_path = exporter.export(
        mock_thread,
        [],
        format="txt",
        current_user_id=mock_client.user_id
    )

    assert output_path.exists()
    # Should still create file with header
    content = output_path.read_text(encoding='utf-8')
    assert "Conversation with" in content
