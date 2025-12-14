"""Message fetching and conversation management."""

import copy
from typing import List, Optional, Dict, Any

from instagrapi import Client
from instagrapi.types import DirectThread, DirectMessage
from instagrapi.extractors import extract_direct_thread, extract_direct_message
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel

from ..utils.exceptions import MessageFetchError, ConversationError, MediaValidationError
from ..utils.logger import get_logger
from ..utils.rate_limiter import instagram_rate_limiter

logger = get_logger(__name__)
console = Console()


class MessageManager:
    """Manage Instagram direct messages and conversations."""

    def __init__(self, client: Client):
        """
        Initialize message manager.

        Args:
            client: Authenticated Instagram client
        """
        self.client = client

    @instagram_rate_limiter
    def get_conversations(self, thread_message_limit: int = 5) -> List[DirectThread]:
        """
        Get all conversations with enhanced error handling.

        Args:
            thread_message_limit: Number of messages to fetch per thread for preview

        Returns:
            List of DirectThread objects

        Raises:
            ConversationError: If fetching conversations fails
        """
        with Progress() as progress:
            task = progress.add_task("[cyan]Fetching conversations...", total=1)

            try:
                # Try standard method first
                threads = self.client.direct_threads(thread_message_limit=thread_message_limit)
                progress.update(task, advance=1)
                logger.info(f"Successfully fetched {len(threads)} conversations")
                return threads

            except Exception as e:
                progress.stop()

                error_str = str(e).lower()
                is_media_error = any(keyword in error_str for keyword in [
                    "clips_metadata", "original_sound_info", "validationerror",
                    "model_type", "input should be a valid dictionary"
                ])

                if is_media_error:
                    logger.warning("Encountered problematic media, trying fallback methods")
                    console.print("[yellow]Encountered problematic media in conversations.[/yellow]")

                    # Try fallback methods
                    threads = self._get_conversations_fallback()
                    if threads:
                        return threads

                    # If all methods fail
                    logger.error("All conversation fetching methods failed")
                    raise ConversationError(
                        "Could not fetch conversations due to problematic media. "
                        "Try updating instagrapi or clearing problematic conversations."
                    )
                else:
                    logger.error(f"Failed to fetch conversations: {e}")
                    raise ConversationError(f"Failed to fetch conversations: {e}")

    def _get_conversations_fallback(self) -> List[DirectThread]:
        """
        Fallback method to get conversations with aggressive error handling.

        Returns:
            List of DirectThread objects
        """
        # Method 1: Minimal message preview
        try:
            console.print("[cyan]Method 1: Fetching with minimal message data...[/cyan]")
            threads = self.client.direct_threads(thread_message_limit=1)
            logger.info("Successfully fetched conversations with minimal data")
            console.print("[green]Successfully fetched conversations.[/green]")
            return threads
        except Exception as e:
            logger.debug(f"Method 1 failed: {e}")

        # Method 2: No message preview
        try:
            console.print("[cyan]Method 2: Fetching without message preview...[/cyan]")
            threads = self.client.direct_threads(thread_message_limit=0)
            logger.info("Successfully fetched conversation list")
            console.print("[green]Successfully fetched conversation list.[/green]")
            return threads
        except Exception as e:
            logger.debug(f"Method 2 failed: {e}")

        # Method 3: Direct API with cleaning
        try:
            console.print("[cyan]Method 3: Using safe API method...[/cyan]")
            threads = self._get_conversations_safe_api()
            return threads
        except Exception as e:
            logger.debug(f"Method 3 failed: {e}")

        return []

    def _get_conversations_safe_api(self) -> List[DirectThread]:
        """
        Use direct API calls with data cleaning.

        Returns:
            List of DirectThread objects

        Raises:
            ConversationError: If API call fails
        """
        try:
            result = self.client.private_request(
                "direct_v2/inbox/",
                params={"visual_message_return_type": "unseen"}
            )

            if not result or "inbox" not in result:
                raise ConversationError("Invalid inbox response")

            threads_data = result["inbox"].get("threads", [])
            logger.info(f"Processing {len(threads_data)} conversations from API")

            safe_threads = []
            skipped_count = 0

            for i, thread_data in enumerate(threads_data):
                try:
                    # Clean thread data
                    cleaned_data = self._clean_thread_data(thread_data)
                    thread = extract_direct_thread(cleaned_data)
                    safe_threads.append(thread)

                except Exception as e:
                    skipped_count += 1
                    logger.debug(f"Skipped thread {i+1}: {e}")

            logger.info(f"Successfully processed {len(safe_threads)} conversations, skipped {skipped_count}")

            if safe_threads:
                console.print(f"[green]Successfully processed {len(safe_threads)} conversations.[/green]")
                if skipped_count > 0:
                    console.print(f"[yellow]Skipped {skipped_count} problematic conversations.[/yellow]")
                return safe_threads
            else:
                raise ConversationError("No conversations could be processed")

        except Exception as e:
            logger.error(f"Safe API method failed: {e}")
            raise ConversationError(f"Safe API method failed: {e}")

    @staticmethod
    def _clean_thread_data(thread_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean problematic data from thread.

        Args:
            thread_data: Raw thread data from API

        Returns:
            Cleaned thread data
        """
        if not isinstance(thread_data, dict):
            return thread_data

        cleaned = copy.deepcopy(thread_data)

        # Clean message items
        if "items" in cleaned and isinstance(cleaned["items"], list):
            safe_items = []
            for item in cleaned["items"][:20]:  # Limit to 20 recent messages
                cleaned_item = MessageManager._clean_media_item(item)
                if cleaned_item:
                    safe_items.append(cleaned_item)
            cleaned["items"] = safe_items

        return cleaned

    @staticmethod
    def _normalize_timestamp_value(value: Any) -> Any:
        """
        Normalize timestamp values that may come in microseconds/milliseconds.

        Pydantic datetime parsing expects seconds; extremely large values blow
        past the year-9999 limit. We progressively divide by 1000 to convert
        milli/microsecond timestamps down to seconds.
        """
        try:
            if isinstance(value, str) and value.isdigit():
                value = int(value)

            if isinstance(value, (int, float)):
                limit_seconds = 253402300799  # datetime max supported (year 9999)
                normalized = int(value)

                # Convert large values (likely ms/us) down to seconds
                for _ in range(2):  # at most microseconds -> divide twice
                    if normalized <= limit_seconds:
                        break
                    normalized = int(normalized / 1000)

                # If still too large, clamp to max supported to avoid crashes
                if normalized > limit_seconds:
                    return limit_seconds

                return normalized
        except Exception:
            pass

        return value

    @staticmethod
    def _normalize_timestamps(data: Any) -> Any:
        """
        Recursively normalize timestamp fields in a data structure.
        """
        if isinstance(data, dict):
            for key, value in list(data.items()):
                data[key] = MessageManager._normalize_timestamps(value)

                if isinstance(data[key], (int, float, str)) and "timestamp" in key:
                    data[key] = MessageManager._normalize_timestamp_value(data[key])

        elif isinstance(data, list):
            return [MessageManager._normalize_timestamps(item) for item in data]

        return data

    @staticmethod
    def _clean_media_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Clean problematic media data from message item.

        Args:
            item: Message item with potentially problematic media

        Returns:
            Cleaned item or None if cleaning fails
        """
        if not isinstance(item, dict):
            return item

        try:
            cleaned = copy.deepcopy(item)

            # Normalize timestamps early to prevent Pydantic overflow errors
            cleaned = MessageManager._normalize_timestamps(cleaned)

            # Handle clips/reels metadata
            if "clip" in cleaned:
                clip_data = cleaned["clip"]

                if isinstance(clip_data, dict) and "clip" in clip_data:
                    clip_data = clip_data["clip"]

                if isinstance(clip_data, dict) and "clips_metadata" in clip_data:
                    metadata = clip_data["clips_metadata"]

                    if isinstance(metadata, dict):
                        # Fix original_sound_info
                        if "original_sound_info" in metadata:
                            sound_info = metadata["original_sound_info"]

                            if sound_info is None or not isinstance(sound_info, dict):
                                metadata["original_sound_info"] = {
                                    "audio_id": "",
                                    "original_audio_title": "",
                                    "progressive_download_url": "",
                                    "dash_manifest": "",
                                    "ig_artist": {"username": "", "pk": 0},
                                    "duration_in_ms": 0,
                                    "is_explicit": False
                                }
                            else:
                                # Ensure required fields
                                sound_info.setdefault("audio_id", "")
                                sound_info.setdefault("original_audio_title", "")
                                sound_info.setdefault("progressive_download_url", "")
                                sound_info.setdefault("dash_manifest", "")
                                sound_info.setdefault("duration_in_ms", 0)
                                sound_info.setdefault("is_explicit", False)

                                if "ig_artist" not in sound_info or not isinstance(sound_info["ig_artist"], dict):
                                    sound_info["ig_artist"] = {"username": "", "pk": 0}
                                else:
                                    sound_info["ig_artist"].setdefault("username", "")
                                    sound_info["ig_artist"].setdefault("pk", 0)

                        # Remove problematic fields
                        for field in ["music_info", "template_info"]:
                            if field in metadata and metadata[field] is None:
                                del metadata[field]

            return cleaned

        except Exception as e:
            logger.debug(f"Failed to clean media item: {e}")
            return None

    @instagram_rate_limiter
    def fetch_messages(
        self,
        thread: DirectThread,
        count: int = 1000
    ) -> List[DirectMessage]:
        """
        Fetch messages from a conversation.

        Args:
            thread: Direct message thread
            count: Number of messages to fetch

        Returns:
            List of DirectMessage objects

        Raises:
            MessageFetchError: If fetching messages fails
        """
        with Progress() as progress:
            task = progress.add_task(f"[cyan]Fetching {count} messages...", total=1)

            try:
                # Try standard method with small test first
                test_messages = self.client.direct_messages(thread.id, min(10, count))

                if test_messages:
                    if count <= 10:
                        progress.update(task, advance=1)
                        logger.info(f"Successfully fetched {len(test_messages)} messages")
                        return test_messages
                    else:
                        # Fetch all requested messages
                        messages = self.client.direct_messages(thread.id, count)
                        progress.update(task, advance=1)
                        logger.info(f"Successfully fetched {len(messages)} messages")
                        return messages
                else:
                    raise MessageFetchError("No messages returned from test fetch")

            except Exception as e:
                progress.stop()

                error_str = str(e).lower()
                is_media_error = any(keyword in error_str for keyword in [
                    "clips_metadata", "original_sound_info", "validationerror",
                    "validation errors", "replymessage", "timestamp_us",
                    "model_type", "unexpected keyword argument"
                ])

                if is_media_error:
                    logger.warning("Encountered problematic media, using safe batch method")
                    console.print("[yellow]Encountered problematic media.[/yellow]")

                    messages = self._fetch_messages_safe_batch(thread.id, count)

                    if messages:
                        logger.info(f"Successfully fetched {len(messages)} messages using safe method")
                        return messages
                    else:
                        logger.warning("No messages could be retrieved")
                        return []
                else:
                    logger.error(f"Failed to fetch messages: {e}")
                    raise MessageFetchError(f"Failed to fetch messages: {e}")

    def _fetch_messages_safe_batch(
        self,
        thread_id: str,
        count: int,
        batch_size: int = 20
    ) -> List[DirectMessage]:
        """
        Fetch messages in safe batches with error handling.

        Args:
            thread_id: Thread ID
            count: Total messages to fetch
            batch_size: Messages per batch

        Returns:
            List of DirectMessage objects
        """
        all_messages = []
        cursor = None
        remaining = count
        consecutive_failures = 0
        max_consecutive_failures = 3

        console.print("[cyan]Fetching messages in safe batches...[/cyan]")

        while remaining > 0 and len(all_messages) < count and consecutive_failures < max_consecutive_failures:
            current_batch_size = min(batch_size, remaining)

            try:
                params = {"limit": current_batch_size}
                if cursor:
                    params["cursor"] = cursor

                result = self.client.private_request(f"direct_v2/threads/{thread_id}/", params=params)

                if not result or "thread" not in result:
                    break

                items = result["thread"].get("items", [])
                if not items:
                    break

                # Process items safely
                batch_messages = []
                for item in items:
                    try:
                        cleaned_item = self._clean_media_item(item)
                        if cleaned_item:
                            message = extract_direct_message(cleaned_item)
                            batch_messages.append(message)
                    except Exception as msg_error:
                        logger.debug(f"Skipped problematic message: {msg_error}")
                        continue

                if batch_messages:
                    all_messages.extend(batch_messages)
                    remaining -= len(batch_messages)
                    cursor = items[-1].get("item_id")
                    consecutive_failures = 0
                    logger.debug(f"Fetched batch of {len(batch_messages)} messages")
                else:
                    consecutive_failures += 1
                    if batch_size > 5:
                        batch_size = max(5, batch_size // 2)

            except Exception as batch_error:
                consecutive_failures += 1
                logger.debug(f"Batch failed: {batch_error}")
                if batch_size > 5:
                    batch_size = max(5, batch_size // 2)

                if consecutive_failures >= max_consecutive_failures:
                    break

        console.print(f"[green]Fetched {len(all_messages)} messages using safe method.[/green]")
        return all_messages

    @staticmethod
    def display_conversations(threads: List[DirectThread]) -> None:
        """
        Display conversations in a formatted table.

        Args:
            threads: List of conversation threads
        """
        table = Table(title="Instagram Conversations")

        table.add_column("ID", justify="right", style="cyan")
        table.add_column("User(s)", style="green")
        table.add_column("Last Message", style="white")

        for i, thread in enumerate(threads, 1):
            users = ", ".join([user.username for user in thread.users])

            # Get last message preview
            last_msg = "[No messages]"
            try:
                if thread.messages and len(thread.messages) > 0:
                    first_msg = thread.messages[0]
                    if hasattr(first_msg, 'text') and first_msg.text:
                        last_msg = first_msg.text
                    elif hasattr(first_msg, 'media') and first_msg.media:
                        last_msg = "[Media message]"
            except Exception:
                pass

            # Truncate long messages
            if last_msg and len(last_msg) > 50:
                last_msg = last_msg[:47] + "..."

            table.add_row(str(i), users, last_msg)

        console.print(table)

    @staticmethod
    def select_conversation(threads: List[DirectThread]) -> DirectThread:
        """
        Let user select a conversation interactively.

        Args:
            threads: List of available threads

        Returns:
            Selected DirectThread

        Raises:
            ConversationError: If selection fails
        """
        MessageManager.display_conversations(threads)

        while True:
            choice = Prompt.ask(
                "Select a conversation by number or enter a username to search",
                default="1"
            )

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(threads):
                    return threads[idx]
                else:
                    console.print("[red]Invalid selection. Please try again.[/red]")
            else:
                # Search by username
                search_term = choice.lower()
                matches = []

                for i, thread in enumerate(threads):
                    for user in thread.users:
                        if search_term in user.username.lower():
                            matches.append((i, thread, user.username))

                if matches:
                    if len(matches) == 1:
                        _, thread, username = matches[0]
                        console.print(f"[green]Found conversation with {username}.[/green]")
                        return thread
                    else:
                        console.print(f"[yellow]Found {len(matches)} matching conversations:[/yellow]")
                        for i, (_, _, username) in enumerate(matches, 1):
                            console.print(f"{i}. {username}")

                        sub_choice = Prompt.ask("Select a conversation by number", default="1")
                        if sub_choice.isdigit() and 1 <= int(sub_choice) <= len(matches):
                            _, thread, _ = matches[int(sub_choice) - 1]
                            return thread
                else:
                    console.print("[red]No conversations found matching that username.[/red]")

    @staticmethod
    def display_messages(
        thread: DirectThread,
        messages: List[DirectMessage],
        client: Client
    ) -> None:
        """
        Display messages in a readable format.

        Args:
            thread: Direct message thread
            messages: List of messages to display
            client: Instagram client (for user info)
        """
        # Get current username
        try:
            current_user = client.user_info(client.user_id)
            current_username = current_user.username
        except:
            current_username = "You"

        usernames = {user.pk: user.username for user in thread.users}
        usernames[client.user_id] = current_username

        sorted_messages = sorted(messages, key=lambda m: m.timestamp)

        console.print(Panel(
            f"[bold]Conversation with {', '.join(u.username for u in thread.users)}[/bold]"
        ))

        for msg in sorted_messages:
            sender = usernames.get(msg.user_id, f"Unknown ({msg.user_id})")
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            message_text = msg.text if msg.text is not None else "[No text content]"

            if msg.user_id == client.user_id:
                console.print(
                    f"[cyan]{timestamp}[/cyan] [bold blue]{sender}:[/bold blue] {message_text}"
                )
            else:
                console.print(
                    f"[cyan]{timestamp}[/cyan] [bold green]{sender}:[/bold green] {message_text}"
                )

            # Display media if present
            try:
                if hasattr(msg, 'media') and msg.media:
                    if hasattr(msg.media, 'media_type'):
                        if msg.media.media_type == 1:
                            url = getattr(msg.media, 'thumbnail_url', 'No URL')
                            console.print(f"[italic]  [Image: {url}][/italic]")
                        elif msg.media.media_type == 2:
                            url = getattr(msg.media, 'video_url', 'No URL')
                            console.print(f"[italic]  [Video: {url}][/italic]")
            except Exception:
                pass
