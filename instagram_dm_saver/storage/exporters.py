"""Export messages to different file formats."""

import json
import csv
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import re

from instagrapi.types import DirectThread, DirectMessage

from ..utils.exceptions import ExportError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MessageExporter:
    """Export messages to various file formats."""

    def __init__(self, save_dir: Path):
        """
        Initialize message exporter.

        Args:
            save_dir: Base directory for saving messages
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize string for safe filename.

        Args:
            name: String to sanitize

        Returns:
            Safe filename string
        """
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    def _get_output_path(
        self,
        thread: DirectThread,
        format: str,
        timestamp: datetime
    ) -> Path:
        """
        Generate output file path.

        Args:
            thread: Direct message thread
            format: File format (txt, json, csv)
            timestamp: Timestamp for filename

        Returns:
            Path to output file
        """
        # Get primary username
        usernames = [user.username for user in thread.users]
        primary_username = usernames[0] if usernames else "unknown"
        safe_username = self._sanitize_filename(primary_username)

        # Create user-specific folder
        user_folder = self.save_dir / safe_username
        user_folder.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        time_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{safe_username}_{time_str}.{format}"

        return user_folder / filename

    def export(
        self,
        thread: DirectThread,
        messages: List[DirectMessage],
        format: str = "txt",
        current_user_id: int = None,
        current_username: str = "You"
    ) -> Path:
        """
        Export messages to file.

        Args:
            thread: Direct message thread
            messages: List of messages to export
            format: Export format (txt, json, csv)
            current_user_id: ID of current user
            current_username: Username of current user

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        try:
            # Get timestamp from first message or use current time
            if messages:
                timestamp = messages[0].timestamp
            else:
                timestamp = datetime.now()

            output_path = self._get_output_path(thread, format, timestamp)

            if format == "txt":
                self._export_txt(thread, messages, output_path, current_user_id, current_username)
            elif format == "json":
                self._export_json(thread, messages, output_path, current_user_id, current_username)
            elif format == "csv":
                self._export_csv(thread, messages, output_path, current_user_id, current_username)
            else:
                raise ExportError(f"Unsupported format: {format}")

            logger.info(f"Exported {len(messages)} messages to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to export messages: {e}")
            raise ExportError(f"Failed to export messages: {e}")

    def _export_txt(
        self,
        thread: DirectThread,
        messages: List[DirectMessage],
        output_path: Path,
        current_user_id: int,
        current_username: str
    ) -> None:
        """Export messages as plain text file."""
        # Create username mapping
        username_map = {user.pk: user.username for user in thread.users}
        if current_user_id:
            username_map[current_user_id] = current_username

        # Sort messages by timestamp
        sorted_messages = sorted(messages, key=lambda m: m.timestamp)

        with open(output_path, 'w', encoding='utf-8') as f:
            # Header
            usernames = [user.username for user in thread.users]
            f.write(f"Conversation with {', '.join(usernames)}\n")
            f.write("=" * 70 + "\n\n")

            current_date = None

            for msg in sorted_messages:
                # Date separator
                msg_date = msg.timestamp.date()
                if current_date != msg_date:
                    if current_date is not None:
                        f.write("\n")

                    date_str = msg_date.strftime("%A, %B %d, %Y")
                    f.write(f"\n{'―' * 25} {date_str} {'―' * 25}\n\n")
                    current_date = msg_date

                # Message
                sender = username_map.get(msg.user_id, f"Unknown ({msg.user_id})")
                timestamp = msg.timestamp.strftime("%H:%M:%S")
                text = msg.text if msg.text is not None else "[No text content]"

                f.write(f"{timestamp} - {sender}: {text}\n")

                # Media info
                try:
                    if hasattr(msg, 'media') and msg.media and hasattr(msg.media, 'media_type'):
                        if msg.media.media_type == 1:  # Image
                            url = getattr(msg.media, 'thumbnail_url', 'No URL')
                            f.write(f"  [Image: {url}]\n")
                        elif msg.media.media_type == 2:  # Video
                            url = getattr(msg.media, 'video_url', 'No URL')
                            f.write(f"  [Video: {url}]\n")
                except Exception as e:
                    logger.debug(f"Could not write media info: {e}")

                f.write("\n")

    def _export_json(
        self,
        thread: DirectThread,
        messages: List[DirectMessage],
        output_path: Path,
        current_user_id: int,
        current_username: str
    ) -> None:
        """Export messages as JSON file."""
        # Create username mapping
        username_map = {user.pk: user.username for user in thread.users}
        if current_user_id:
            username_map[current_user_id] = current_username

        # Sort messages
        sorted_messages = sorted(messages, key=lambda m: m.timestamp)

        # Build JSON structure
        data = {
            "conversation_info": {
                "participants": [user.username for user in thread.users],
                "thread_id": thread.id,
                "export_time": datetime.now().isoformat(),
                "message_count": len(sorted_messages)
            },
            "messages": []
        }

        for msg in sorted_messages:
            sender = username_map.get(msg.user_id, f"Unknown ({msg.user_id})")

            message_data = {
                "timestamp": msg.timestamp.isoformat(),
                "sender": sender,
                "sender_id": msg.user_id,
                "text": msg.text,
                "message_id": getattr(msg, 'id', None)
            }

            # Add media info
            try:
                if hasattr(msg, 'media') and msg.media and hasattr(msg.media, 'media_type'):
                    media_type = "image" if msg.media.media_type == 1 else "video" if msg.media.media_type == 2 else "other"
                    message_data["media"] = {
                        "type": media_type,
                        "thumbnail_url": getattr(msg.media, 'thumbnail_url', None),
                        "video_url": getattr(msg.media, 'video_url', None) if msg.media.media_type == 2 else None
                    }
            except Exception as e:
                logger.debug(f"Could not add media info: {e}")

            data["messages"].append(message_data)

        # Write JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _export_csv(
        self,
        thread: DirectThread,
        messages: List[DirectMessage],
        output_path: Path,
        current_user_id: int,
        current_username: str
    ) -> None:
        """Export messages as CSV file."""
        # Create username mapping
        username_map = {user.pk: user.username for user in thread.users}
        if current_user_id:
            username_map[current_user_id] = current_username

        # Sort messages
        sorted_messages = sorted(messages, key=lambda m: m.timestamp)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "Timestamp",
                "Date",
                "Time",
                "Sender",
                "Sender_ID",
                "Message",
                "Media_Type",
                "Media_URL"
            ])

            # Messages
            for msg in sorted_messages:
                sender = username_map.get(msg.user_id, f"Unknown ({msg.user_id})")

                media_type = ""
                media_url = ""

                try:
                    if hasattr(msg, 'media') and msg.media and hasattr(msg.media, 'media_type'):
                        if msg.media.media_type == 1:
                            media_type = "Image"
                            media_url = getattr(msg.media, 'thumbnail_url', "")
                        elif msg.media.media_type == 2:
                            media_type = "Video"
                            media_url = getattr(msg.media, 'video_url', "")
                except Exception as e:
                    logger.debug(f"Could not extract media info: {e}")

                writer.writerow([
                    msg.timestamp.isoformat(),
                    msg.timestamp.strftime("%Y-%m-%d"),
                    msg.timestamp.strftime("%H:%M:%S"),
                    sender,
                    msg.user_id,
                    msg.text or "[No text content]",
                    media_type,
                    media_url
                ])
