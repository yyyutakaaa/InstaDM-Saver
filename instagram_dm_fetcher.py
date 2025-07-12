import os
import json
import getpass
import csv
from pathlib import Path
from typing import Dict, List, Optional, Union

from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table
from instagrapi import Client
from instagrapi.types import UserShort, DirectThread, DirectMessage
import keyring

# Initialize Rich console for better output
console = Console()

# Constants
CONFIG_DIR = Path.home() / ".instagram_dm_fetcher"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
SESSION_FILE = CONFIG_DIR / "session.json"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_MESSAGE_COUNT = 1000
DEFAULT_SAVE_DIR = Path.home() / "Instagram_DM_Fetcher_Chats"
KEYRING_SERVICE = "instagram_dm_fetcher"

def load_config() -> Dict[str, str]:
    """Load configuration settings."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config
        except (json.JSONDecodeError, KeyError):
            console.print("[yellow]Config file is invalid.[/yellow]")
    
    # Default configuration
    return {
        "save_dir": str(DEFAULT_SAVE_DIR),
        "credential_storage": "keyring"
    }

def save_config(config: Dict[str, str]) -> None:
    """Save configuration settings."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
    console.print("[green]Configuration saved.[/green]")

def setup_config_dir() -> None:
    """Create configuration directory if it doesn't exist."""
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)
        console.print("[green]Created config directory.[/green]")
    
    # Make sure default save directory exists
    config = load_config()
    save_dir = Path(config.get("save_dir", str(DEFAULT_SAVE_DIR)))
    
    if not save_dir.exists():
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Created save directory: {save_dir}[/green]")
        except Exception as e:
            console.print(f"[yellow]Could not create save directory: {str(e)}[/yellow]")
            config["save_dir"] = str(DEFAULT_SAVE_DIR)
            DEFAULT_SAVE_DIR.mkdir(parents=True, exist_ok=True)
            save_config(config)

def save_credentials_keyring(username: str, password: str) -> bool:
    """Save credentials to system keyring."""
    try:
        keyring.set_password(KEYRING_SERVICE, username, password)
        console.print("[green]Credentials saved securely to system keyring.[/green]")
        return True
    except Exception as e:
        console.print(f"[yellow]Could not save to keyring: {e}[/yellow]")
        return False

def load_credentials_keyring(username: str) -> Optional[str]:
    """Load password from system keyring."""
    try:
        password = keyring.get_password(KEYRING_SERVICE, username)
        return password
    except Exception as e:
        console.print(f"[yellow]Could not load from keyring: {e}[/yellow]")
        return None

def delete_credentials_keyring(username: str) -> bool:
    """Delete credentials from system keyring."""
    try:
        keyring.delete_password(KEYRING_SERVICE, username)
        console.print("[green]Credentials removed from keyring.[/green]")
        return True
    except Exception as e:
        console.print(f"[yellow]Could not delete from keyring: {e}[/yellow]")
        return False

def save_credentials_file(username: str, password: str) -> bool:
    """Save credentials to file (legacy fallback)."""
    try:
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump({"username": username, "password": password}, f)
        console.print("[green]Credentials saved to file.[/green]")
        return True
    except Exception as e:
        console.print(f"[yellow]Could not save to file: {e}[/yellow]")
        return False

def load_credentials_file() -> Dict[str, str]:
    """Load credentials from file (legacy fallback)."""
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                credentials = json.load(f)
                return credentials
        except (json.JSONDecodeError, KeyError):
            console.print("[yellow]Credentials file is invalid.[/yellow]")
    return {}

def get_credential_storage_method() -> str:
    """Let user choose credential storage method."""
    methods = {
        "1": "System Keyring (Recommended)",
        "2": "File Storage (Less Secure)",
        "3": "Environment Variables Only",
        "4": "No Storage (Always Ask)"
    }
    
    console.print("\n[bold]Choose credential storage method:[/bold]")
    for key, value in methods.items():
        console.print(f"{key}. {value}")
    
    choice = Prompt.ask("Select method", choices=list(methods.keys()), default="1")
    return choice

def save_credentials(username: str, password: str) -> None:
    """Save credentials using configured method."""
    config = load_config()
    storage_method = config.get("credential_storage", "keyring")
    
    if storage_method == "keyring":
        success = save_credentials_keyring(username, password)
        if not success:
            console.print("[yellow]Keyring failed, trying file storage as fallback...[/yellow]")
            save_credentials_file(username, password)
    elif storage_method == "file":
        save_credentials_file(username, password)
    elif storage_method == "env":
        console.print("[yellow]Set IG_USERNAME and IG_PASSWORD environment variables.[/yellow]")
    else:
        console.print("[yellow]Credentials will not be saved.[/yellow]")

def load_credentials() -> Dict[str, str]:
    """Load saved credentials using configured method."""
    # First check environment variables
    load_dotenv()
    username = os.getenv("IG_USERNAME")
    password = os.getenv("IG_PASSWORD")
    
    if username and password:
        return {"username": username, "password": password}
    
    config = load_config()
    storage_method = config.get("credential_storage", "keyring")
    
    if storage_method == "keyring":
        # Try to load from keyring
        if username:  # We have username from env, try to get password from keyring
            password = load_credentials_keyring(username)
            if password:
                return {"username": username, "password": password}
        
        # Check if we have any saved usernames in keyring
        file_creds = load_credentials_file()
        if file_creds.get("username"):
            username = file_creds["username"]
            password = load_credentials_keyring(username)
            if password:
                return {"username": username, "password": password}
    
    elif storage_method == "file":
        return load_credentials_file()
    
    return {}

def configure_credentials():
    """Configure credential storage method."""
    config = load_config()
    current_method = config.get("credential_storage", "keyring")
    
    method_names = {
        "keyring": "System Keyring",
        "file": "File Storage",
        "env": "Environment Variables Only",
        "none": "No Storage"
    }
    
    console.print(f"Current method: [cyan]{method_names.get(current_method, 'Unknown')}[/cyan]")
    
    if Confirm.ask("Do you want to change the credential storage method?"):
        choice = get_credential_storage_method()
        
        method_mapping = {
            "1": "keyring",
            "2": "file", 
            "3": "env",
            "4": "none"
        }
        
        new_method = method_mapping[choice]
        config["credential_storage"] = new_method
        save_config(config)
        
        console.print(f"[green]Credential storage method updated to: {method_names[new_method]}[/green]")
        
        # If switching from file to keyring, offer to migrate
        if current_method == "file" and new_method == "keyring":
            if Confirm.ask("Do you want to migrate existing file credentials to keyring?"):
                file_creds = load_credentials_file()
                if file_creds.get("username") and file_creds.get("password"):
                    if save_credentials_keyring(file_creds["username"], file_creds["password"]):
                        if Confirm.ask("Migration successful! Delete the old credentials file?"):
                            try:
                                CREDENTIALS_FILE.unlink()
                                console.print("[green]Old credentials file deleted.[/green]")
                            except Exception as e:
                                console.print(f"[yellow]Could not delete old file: {e}[/yellow]")
        
        # If switching from keyring to file, warn about security
        elif current_method == "keyring" and new_method == "file":
            console.print("[yellow]Warning: File storage is less secure than keyring.[/yellow]")

def manage_saved_credentials():
    """Manage saved credentials."""
    config = load_config()
    storage_method = config.get("credential_storage", "keyring")
    
    if storage_method == "keyring":
        # Try to find saved credentials
        file_creds = load_credentials_file()
        if file_creds.get("username"):
            username = file_creds["username"]
            if load_credentials_keyring(username):
                console.print(f"Found saved credentials for: [cyan]{username}[/cyan]")
                if Confirm.ask("Do you want to delete these credentials?"):
                    delete_credentials_keyring(username)
            else:
                console.print("No credentials found in keyring.")
        else:
            console.print("No saved credentials found.")
    
    elif storage_method == "file":
        if CREDENTIALS_FILE.exists():
            creds = load_credentials_file()
            if creds.get("username"):
                console.print(f"Found saved credentials for: [cyan]{creds['username']}[/cyan]")
                if Confirm.ask("Do you want to delete these credentials?"):
                    try:
                        CREDENTIALS_FILE.unlink()
                        console.print("[green]Credentials file deleted.[/green]")
                    except Exception as e:
                        console.print(f"[red]Could not delete file: {e}[/red]")
            else:
                console.print("Credentials file is invalid.")
        else:
            console.print("No credentials file found.")
    
    else:
        console.print("No credentials are saved with the current storage method.")

def login_to_instagram() -> Client:
    """Log in to Instagram and return a client using a single persistent session."""
    client = Client()

    credentials = load_credentials()

    if SESSION_FILE.exists():
        try:
            console.print("Attempting to load saved session...")
            client.load_settings(SESSION_FILE)
            # Calling login with stored credentials will reuse the session
            if credentials.get("username") and credentials.get("password"):
                client.login(credentials["username"], credentials["password"])
            else:
                client.get_timeline_feed()  # Fallback check
            console.print("[green]Successfully loaded session.[/green]")
            return client
        except Exception as e:
            console.print(f"[yellow]Failed to load saved session: {str(e)}[/yellow]")

    if not credentials:
        console.print("No saved credentials found.")
        username = Prompt.ask("Enter your Instagram username")
        password = getpass.getpass("Enter your Instagram password: ")
    else:
        username = credentials.get("username")
        password = credentials.get("password")
        console.print(f"Using saved credentials for [bold]{username}[/bold]")

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Logging in to Instagram...", total=1)
            try:
                client.login(username, password)
            except Exception as e:
                if "Two-factor authentication required" in str(e):
                    progress.stop()
                    console.print("[yellow]Two-factor authentication required[/yellow]")
                    verification_code = Prompt.ask("Enter the verification code from your authenticator app")
                    client.login(username, password, verification_code=verification_code)
                else:
                    raise e
            progress.update(task, advance=1)
        
        console.print("[green]Login successful![/green]")
        
        client.dump_settings(SESSION_FILE)
        if not credentials:  # Only ask if we didn't have saved credentials
            if Confirm.ask("Save credentials for future use?"):
                save_credentials(username, password)
        
        return client
    except Exception as e:
        console.print(f"[red]Login failed: {str(e)}[/red]")
        raise

def clean_media_item(item: dict) -> Optional[dict]:
    """Clean problematic media data from a message item."""
    if not isinstance(item, dict):
        return item
    
    try:
        import copy
        cleaned_item = copy.deepcopy(item)
        
        # Handle clips/reels which are causing validation errors
        if "clip" in cleaned_item:
            clip_data = cleaned_item["clip"]
            
            # Handle nested clip structure
            if isinstance(clip_data, dict) and "clip" in clip_data:
                clip_data = clip_data["clip"]
            
            if isinstance(clip_data, dict) and "clips_metadata" in clip_data:
                clips_metadata = clip_data["clips_metadata"]
                
                if isinstance(clips_metadata, dict):
                    # Fix the original_sound_info validation error
                    if "original_sound_info" in clips_metadata:
                        original_sound = clips_metadata["original_sound_info"]
                        
                        # If it's None or invalid, provide a default structure
                        if original_sound is None or not isinstance(original_sound, dict):
                            clips_metadata["original_sound_info"] = {
                                "audio_id": "",
                                "original_audio_title": "",
                                "progressive_download_url": "",
                                "dash_manifest": "",
                                "ig_artist": {"username": "", "pk": 0},
                                "duration_in_ms": 0,
                                "is_explicit": False
                            }
                        else:
                            # Ensure required fields exist
                            required_fields = {
                                "audio_id": "",
                                "original_audio_title": "",
                                "progressive_download_url": "",
                                "dash_manifest": "",
                                "duration_in_ms": 0,
                                "is_explicit": False
                            }
                            
                            for field, default in required_fields.items():
                                if field not in original_sound:
                                    original_sound[field] = default
                            
                            # Ensure ig_artist has correct structure
                            if "ig_artist" not in original_sound or not isinstance(original_sound["ig_artist"], dict):
                                original_sound["ig_artist"] = {"username": "", "pk": 0}
                            else:
                                if "username" not in original_sound["ig_artist"]:
                                    original_sound["ig_artist"]["username"] = ""
                                if "pk" not in original_sound["ig_artist"]:
                                    original_sound["ig_artist"]["pk"] = 0
                    
                    # Clean other potentially problematic fields
                    problematic_fields = ["music_info", "template_info"]
                    for field in problematic_fields:
                        if field in clips_metadata and clips_metadata[field] is None:
                            del clips_metadata[field]
        
        # Clean other media types that might cause issues
        media_fields_to_clean = ["media", "video", "photo"]
        for field in media_fields_to_clean:
            if field in cleaned_item and cleaned_item[field]:
                media_data = cleaned_item[field]
                if isinstance(media_data, dict):
                    # Remove fields that commonly cause validation errors
                    fields_to_remove = ["clips_metadata", "original_sound_info"]
                    for remove_field in fields_to_remove:
                        if remove_field in media_data:
                            del media_data[remove_field]
        
        return cleaned_item
        
    except Exception as e:
        # If cleaning fails, return None to skip this item
        console.print(f"[yellow]Skipping problematic media item: {str(e)[:50]}...[/yellow]")
        return None

def clean_thread_data(thread_data: dict) -> dict:
    """Clean problematic data from thread information."""
    if not isinstance(thread_data, dict):
        return thread_data
    
    # Create a deep copy to avoid modifying original
    import copy
    cleaned = copy.deepcopy(thread_data)
    
    # Clean items (messages)
    if "items" in cleaned and isinstance(cleaned["items"], list):
        safe_items = []
        for item in cleaned["items"]:
            if isinstance(item, dict):
                # Clean problematic media data
                cleaned_item = clean_media_item(item)
                if cleaned_item:  # Only add if cleaning succeeded
                    safe_items.append(cleaned_item)
        cleaned["items"] = safe_items[:20]  # Limit to first 20 items for safety
    
    return cleaned

def get_conversations_safe_api(client: Client) -> List[DirectThread]:
    """Use direct API calls with better error handling."""
    try:
        # Use the private request method to get raw inbox data
        result = client.private_request("direct_v2/inbox/", params={"visual_message_return_type": "unseen"})
        
        if not result or "inbox" not in result:
            raise Exception("Invalid inbox response from Instagram API")
        
        inbox = result["inbox"]
        threads_data = inbox.get("threads", [])
        
        if not threads_data:
            console.print("[yellow]No conversations found in inbox.[/yellow]")
            return []
        
        console.print(f"[cyan]Processing {len(threads_data)} conversations...[/cyan]")
        
        safe_threads = []
        skipped_count = 0
        
        for i, thread_data in enumerate(threads_data):
            try:
                # Clean the thread data before processing
                cleaned_thread_data = clean_thread_data(thread_data)
                
                # Extract thread using instagrapi's extractor
                from instagrapi.extractors import extract_direct_thread
                thread = extract_direct_thread(cleaned_thread_data)
                
                safe_threads.append(thread)
                
            except Exception as thread_error:
                skipped_count += 1
                console.print(f"[yellow]Skipped thread {i+1}: {str(thread_error)[:50]}...[/yellow]")
                continue
        
        if safe_threads:
            console.print(f"[green]Successfully processed {len(safe_threads)} conversations.[/green]")
            if skipped_count > 0:
                console.print(f"[yellow]Skipped {skipped_count} problematic conversations.[/yellow]")
            return safe_threads
        else:
            raise Exception("No safe conversations could be processed")
            
    except Exception as e:
        console.print(f"[red]Safe API method failed: {str(e)[:100]}...[/red]")
        raise

def get_conversations(client: Client) -> List[DirectThread]:
    """Get all conversations with enhanced error handling for problematic media."""
    with Progress() as progress:
        task = progress.add_task("[cyan]Fetching conversations...", total=1)
        
        try:
            # Try the standard method first
            threads = client.direct_threads(thread_message_limit=5)  # Limit messages to reduce issues
            progress.update(task, advance=1)
            return threads
        except Exception as e:
            progress.stop()
            
            # Check if it's a validation error related to media
            error_str = str(e).lower()
            is_media_error = any(keyword in error_str for keyword in [
                "clips_metadata", "original_sound_info", "validationerror", 
                "model_type", "input should be a valid dictionary"
            ])
            
            if is_media_error:
                console.print("[yellow]Encountered problematic media in conversations.[/yellow]")
                console.print("[yellow]Trying enhanced error handling methods...[/yellow]")
                
                # Method 1: Try with very limited messages
                try:
                    console.print("[cyan]Method 1: Fetching with minimal message data...[/cyan]")
                    threads = client.direct_threads(thread_message_limit=1)
                    console.print("[green]Successfully fetched conversations with minimal data.[/green]")
                    return threads
                except Exception as e1:
                    console.print(f"[yellow]Method 1 failed: {str(e1)[:50]}...[/yellow]")
                
                # Method 2: Try with no message preview
                try:
                    console.print("[cyan]Method 2: Fetching conversation list without messages...[/cyan]")
                    threads = client.direct_threads(thread_message_limit=0)
                    console.print("[green]Successfully fetched conversation list.[/green]")
                    console.print("[yellow]Note: Message previews not available.[/yellow]")
                    return threads
                except Exception as e2:
                    console.print(f"[yellow]Method 2 failed: {str(e2)[:50]}...[/yellow]")
                
                # Method 3: Use safe API calls
                try:
                    console.print("[cyan]Method 3: Using enhanced API method...[/cyan]")
                    threads = get_conversations_safe_api(client)
                    return threads
                except Exception as e3:
                    console.print(f"[yellow]Method 3 failed: {str(e3)[:50]}...[/yellow]")
                
                # If all methods fail, provide helpful error message
                console.print("\n[bold red]Could not fetch conversations due to problematic media.[/bold red]")
                console.print("[yellow]This is usually caused by Instagram Reels/clips with invalid metadata.[/yellow]")
                console.print("\n[bold]Possible solutions:[/bold]")
                console.print("1. Update instagrapi: [cyan]pip install --upgrade instagrapi[/cyan]")
                console.print("2. Try again later (Instagram may have API issues)")
                console.print("3. Clear problematic conversations from Instagram mobile app")
                console.print("4. Report this issue to the instagrapi project on GitHub")
                
                raise Exception("All conversation fetching methods failed due to problematic media")
            else:
                # Different error, re-raise with original message
                raise e

def display_conversations(threads: List[DirectThread]) -> None:
    """Display all conversations in a table."""
    table = Table(title="Instagram Conversations")
    
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("User(s)", style="green")
    table.add_column("Last Message", style="white")
    
    for i, thread in enumerate(threads, 1):
        users = ", ".join([user.username for user in thread.users])
        
        # Safely get last message
        last_msg = "[No text content]"
        try:
            if thread.messages and len(thread.messages) > 0:
                first_msg = thread.messages[0]
                if hasattr(first_msg, 'text') and first_msg.text:
                    last_msg = first_msg.text
                elif hasattr(first_msg, 'media') and first_msg.media:
                    last_msg = "[Media message]"
        except Exception:
            last_msg = "[No messages]"
        
        # Truncate long messages
        if last_msg and len(last_msg) > 50:
            last_msg = last_msg[:47] + "..."
        
        table.add_row(str(i), users, last_msg)
    
    console.print(table)

def select_conversation(threads: List[DirectThread]) -> DirectThread:
    """Let user select a conversation."""
    display_conversations(threads)
    
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
            search_term = choice.lower()
            matches = []
            
            for i, thread in enumerate(threads):
                for user in thread.users:
                    if search_term in user.username.lower():
                        matches.append((i, thread, user.username))
            
            if matches:
                if len(matches) == 1:
                    idx, thread, username = matches[0]
                    console.print(f"[green]Found conversation with {username}.[/green]")
                    return thread
                else:
                    console.print(f"[yellow]Found {len(matches)} matching conversations:[/yellow]")
                    for i, (idx, thread, username) in enumerate(matches, 1):
                        console.print(f"{i}. {username}")
                    
                    sub_choice = Prompt.ask("Select a conversation by number", default="1")
                    if sub_choice.isdigit() and 1 <= int(sub_choice) <= len(matches):
                        idx, thread, _ = matches[int(sub_choice) - 1]
                        return thread
            else:
                console.print("[red]No conversations found matching that username.[/red]")

def fetch_messages_safe_batch(client: Client, thread_id: str, count: int, batch_size: int = 20) -> List[DirectMessage]:
    """Fetch messages in small, safe batches with aggressive error handling."""
    all_messages = []
    cursor = None
    remaining = count
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    while remaining > 0 and len(all_messages) < count and consecutive_failures < max_consecutive_failures:
        current_batch_size = min(batch_size, remaining)
        
        try:
            console.print(f"[cyan]Fetching batch of {current_batch_size} messages...[/cyan]")
            
            # Use the private API to get messages with better control
            params = {
                "limit": current_batch_size
            }
            if cursor:
                params["cursor"] = cursor
            
            result = client.private_request(f"direct_v2/threads/{thread_id}/", params=params)
            
            if not result or "thread" not in result:
                console.print("[yellow]No thread data in response.[/yellow]")
                break
            
            thread_data = result["thread"]
            items = thread_data.get("items", [])
            
            if not items:
                console.print("[yellow]No more messages available.[/yellow]")
                break
            
            # Process items safely
            batch_messages = []
            for item in items:
                try:
                    # Clean the item before processing
                    cleaned_item = clean_media_item(item)
                    if cleaned_item:
                        # Extract message using instagrapi
                        from instagrapi.extractors import extract_direct_message
                        message = extract_direct_message(cleaned_item)
                        batch_messages.append(message)
                except Exception as msg_error:
                    # Skip problematic individual messages
                    console.print(f"[yellow]Skipped problematic message: {str(msg_error)[:30]}...[/yellow]")
                    continue
            
            if batch_messages:
                all_messages.extend(batch_messages)
                remaining -= len(batch_messages)
                cursor = items[-1].get("item_id")  # Get cursor for next batch
                consecutive_failures = 0  # Reset failure counter
                console.print(f"[green]Successfully fetched {len(batch_messages)} messages.[/green]")
            else:
                consecutive_failures += 1
                console.print(f"[yellow]No valid messages in this batch. Attempt {consecutive_failures}/{max_consecutive_failures}[/yellow]")
                
                # Try smaller batch size on failure
                if batch_size > 5:
                    batch_size = max(5, batch_size // 2)
                    console.print(f"[yellow]Reducing batch size to {batch_size}[/yellow]")
                
        except Exception as batch_error:
            consecutive_failures += 1
            console.print(f"[yellow]Batch failed ({consecutive_failures}/{max_consecutive_failures}): {str(batch_error)[:50]}...[/yellow]")
            
            # Try smaller batch size on failure
            if batch_size > 5:
                batch_size = max(5, batch_size // 2)
                console.print(f"[yellow]Reducing batch size to {batch_size}[/yellow]")
            
            if consecutive_failures >= max_consecutive_failures:
                console.print("[red]Too many consecutive failures, stopping batch fetch.[/red]")
                break
    
    return all_messages

def fetch_messages(client: Client, thread: DirectThread, count: int = DEFAULT_MESSAGE_COUNT) -> List[DirectMessage]:
    """Fetch messages from a conversation with enhanced error handling for problematic media."""
    with Progress() as progress:
        task = progress.add_task(f"[cyan]Fetching {count} messages...", total=1)
        
        try:
            # Try the standard method first with a small limit to test
            test_messages = client.direct_messages(thread.id, min(10, count))
            
            # If test worked, try to get all requested messages
            if test_messages:
                if count <= 10:
                    progress.update(task, advance=1)
                    return test_messages
                else:
                    # Try to get more messages
                    messages = client.direct_messages(thread.id, count)
                    progress.update(task, advance=1)
                    return messages
            else:
                raise Exception("No messages returned from test fetch")
                
        except Exception as e:
            progress.stop()
            
            error_str = str(e).lower()
            is_media_error = any(keyword in error_str for keyword in [
                "clips_metadata", "original_sound_info", "validationerror",
                "model_type", "input should be a valid dictionary", "unexpected keyword argument"
            ])
            
            if is_media_error:
                console.print("[yellow]Encountered problematic media in messages.[/yellow]")
                console.print("[yellow]Trying safe batch fetching method...[/yellow]")
                
                try:
                    messages = fetch_messages_safe_batch(client, thread.id, count, batch_size=20)
                    
                    if messages:
                        console.print(f"[green]Successfully fetched {len(messages)} messages using safe method.[/green]")
                        return messages
                    else:
                        console.print("[yellow]No messages could be retrieved safely.[/yellow]")
                        return []
                        
                except Exception as safe_error:
                    console.print(f"[red]Safe batch method failed: {str(safe_error)[:50]}...[/red]")
                    
                    # Last resort: try to get just a few recent messages
                    try:
                        console.print("[cyan]Attempting to fetch just the most recent messages...[/cyan]")
                        recent_messages = client.direct_messages(thread.id, 5)
                        if recent_messages:
                            console.print(f"[green]Retrieved {len(recent_messages)} recent messages.[/green]")
                            return recent_messages
                        else:
                            return []
                    except Exception:
                        console.print("[red]All message fetching methods failed.[/red]")
                        return []
            else:
                # Different error, re-raise
                raise e

def display_messages(thread: DirectThread, messages: List[DirectMessage], client: Client) -> None:
    """Display messages in a readable format."""
    # Get the logged-in user's actual username
    try:
        current_user = client.user_info(client.user_id)
        current_username = current_user.username
    except:
        # Fallback if we can't get the username
        current_username = "You"
    
    usernames = {user.pk: user.username for user in thread.users}
    usernames[client.user_id] = current_username
    
    sorted_messages = sorted(messages, key=lambda m: m.timestamp)
    
    console.print(Panel(f"[bold]Conversation with {', '.join(u.username for u in thread.users)}[/bold]"))
    
    for msg in sorted_messages:
        sender = usernames.get(msg.user_id, f"Unknown ({msg.user_id})")
        timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Handle None text gracefully
        message_text = msg.text if msg.text is not None else "None"
        
        if msg.user_id == client.user_id:
            console.print(f"[cyan]{timestamp}[/cyan] [bold blue]{sender}:[/bold blue] {message_text}")
        else:
            console.print(f"[cyan]{timestamp}[/cyan] [bold green]{sender}:[/bold green] {message_text}")
        
        # Display media if present
        try:
            if hasattr(msg, 'media') and msg.media:
                if hasattr(msg.media, 'media_type'):
                    if msg.media.media_type == 1:  # Image
                        thumbnail_url = getattr(msg.media, 'thumbnail_url', 'No URL available')
                        console.print(f"[italic][Image: {thumbnail_url}][/italic]")
                    elif msg.media.media_type == 2:  # Video
                        video_url = getattr(msg.media, 'video_url', 'No URL available')
                        console.print(f"[italic][Video: {video_url}][/italic]")
                    else:
                        console.print(f"[italic][Media: Type {msg.media.media_type}][/italic]")
                else:
                    console.print(f"[italic][Media attachment][/italic]")
        except Exception as media_error:
            console.print(f"[italic][Media - display error: {str(media_error)[:30]}...][/italic]")

def choose_file_format() -> str:
    """Let user choose the file format for saving messages."""
    formats = {
        "1": "TXT - Plain text file (human readable)",
        "2": "JSON - Structured data format",
        "3": "CSV - Spreadsheet compatible format"
    }
    
    console.print("\n[bold]Choose file format:[/bold]")
    for key, value in formats.items():
        console.print(f"{key}. {value}")
    
    choice = Prompt.ask("Select format", choices=list(formats.keys()), default="1")
    
    format_mapping = {
        "1": "txt",
        "2": "json", 
        "3": "csv"
    }
    
    return format_mapping[choice]

def save_messages_to_file(thread: DirectThread, messages: List[DirectMessage], client: Client, file_format: str = None) -> str:
    """Save messages to a file in specified format and return the filename."""
    import datetime
    import re
    import csv
    
    # Choose format if not provided
    if file_format is None:
        file_format = choose_file_format()
    
    try:
        # Load save directory from config
        config = load_config()
        base_save_dir = Path(config.get("save_dir", str(DEFAULT_SAVE_DIR)))
        
        # Sanitize username for safe filename
        usernames = [user.username for user in thread.users]
        primary_username = usernames[0] if usernames else "unknown"
        # Remove invalid filename characters
        safe_username = re.sub(r'[\\/*?:"<>|]', "_", primary_username)
        
        # Create user-specific folder inside the base save directory
        save_folder = base_save_dir / safe_username
        
        # Create directory with proper error handling
        try:
            save_folder.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # If permission error, use home directory as fallback
            fallback_dir = Path.home() / "Instagram_DM_Fetcher_Chats" / safe_username
            fallback_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"[yellow]Permission error with configured save directory. Using fallback: {fallback_dir}[/yellow]")
            save_folder = fallback_dir
        
        # Generate filename with timestamp
        if messages:
            current_time = messages[0].timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        else:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            
        filename = save_folder / f"{safe_username}_{current_time}.{file_format}"
        
        # Get the logged-in user's actual username
        try:
            current_user = client.user_info(client.user_id)
            current_username = current_user.username
        except:
            # Fallback if we can't get the username
            current_username = "You"
        
        username_map = {user.pk: user.username for user in thread.users}
        username_map[client.user_id] = current_username
        
        sorted_messages = sorted(messages, key=lambda m: m.timestamp)
        
        if file_format == "txt":
            # Original TXT format
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Conversation with {', '.join(usernames)}\n")
                f.write("=" * 50 + "\n\n")
                
                current_date = None
                
                for msg in sorted_messages:
                    msg_date = msg.timestamp.date()
                    if current_date != msg_date:
                        if current_date is not None:
                            f.write("\n")
                        
                        date_str = msg_date.strftime("%A, %B %d, %Y")
                        f.write(f"\n――――― {date_str} ―――――\n\n")
                        current_date = msg_date
                    
                    sender = username_map.get(msg.user_id, f"Unknown ({msg.user_id})")
                    timestamp = msg.timestamp.strftime("%H:%M:%S")
                    
                    msg_text = msg.text if msg.text is not None else "[No text content]"
                    f.write(f"{timestamp} - {sender}: {msg_text}\n")
                    
                    # Handle media safely
                    try:
                        if hasattr(msg, 'media') and msg.media and hasattr(msg.media, 'media_type'):
                            if msg.media.media_type == 1:  # Image
                                thumbnail_url = getattr(msg.media, 'thumbnail_url', 'No URL available')
                                f.write(f"[Image: {thumbnail_url}]\n")
                            elif msg.media.media_type == 2:  # Video
                                video_url = getattr(msg.media, 'video_url', 'No URL available')
                                f.write(f"[Video: {video_url}]\n")
                    except Exception:
                        f.write("[Media attachment - unable to display]\n")
                    
                    f.write("\n")
        
        elif file_format == "json":
            # JSON format
            messages_data = {
                "conversation_info": {
                    "participants": usernames,
                    "export_time": datetime.datetime.now().isoformat(),
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
                
                # Add media information if present
                try:
                    if hasattr(msg, 'media') and msg.media and hasattr(msg.media, 'media_type'):
                        message_data["media"] = {
                            "type": "image" if msg.media.media_type == 1 else "video" if msg.media.media_type == 2 else "other",
                            "thumbnail_url": getattr(msg.media, 'thumbnail_url', None),
                            "video_url": getattr(msg.media, 'video_url', None) if msg.media.media_type == 2 else None
                        }
                except Exception:
                    message_data["media"] = {"type": "unknown", "error": "Could not parse media data"}
                
                messages_data["messages"].append(message_data)
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(messages_data, f, indent=2, ensure_ascii=False, default=str)
        
        elif file_format == "csv":
            # CSV format
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(["Timestamp", "Date", "Time", "Sender", "Sender_ID", "Message", "Media_Type", "Media_URL"])
                
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
                    except Exception:
                        media_type = "Unknown"
                        media_url = "Error parsing media"
                    
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
                
        return str(filename)
    except Exception as e:
        console.print(f"[bold red]Error saving messages: {str(e)}[/bold red]")
        # Create a default fallback file in the user's home directory
        fallback_file = Path.home() / f"instagram_messages_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            # Get current username for fallback
            try:
                current_user = client.user_info(client.user_id)
                current_username = current_user.username
            except:
                current_username = "You"
            
            with open(fallback_file, "w", encoding="utf-8") as f:
                f.write(f"Conversation with {', '.join(usernames) if 'usernames' in locals() else 'unknown'}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Error occurred while saving original file: {str(e)}\n\n")
                # Try to save at least some message content
                if 'sorted_messages' in locals() and sorted_messages:
                    for msg in sorted_messages[:10]:  # Save at least first 10 messages
                        sender = current_username if msg.user_id == client.user_id else f"Other ({msg.user_id})"
                        f.write(f"{msg.timestamp.strftime('%H:%M:%S')} - {sender}: {msg.text or '[No text content]'}\n\n")
            return str(fallback_file)
        except Exception as fallback_error:
            console.print(f"[bold red]Failed to save fallback file: {str(fallback_error)}[/bold red]")
            return "Error: Could not save file"

def configure_save_directory():
    """Configure the save directory."""
    config = load_config()
    current_dir = config.get("save_dir", str(DEFAULT_SAVE_DIR))
    
    console.print(f"Current save directory: [cyan]{current_dir}[/cyan]")
    
    if Confirm.ask("Do you want to change the save directory?"):
        new_dir = Prompt.ask("Enter new save directory path", default=current_dir)
        
        try:
            # Test if the directory is valid and writable
            save_dir = Path(new_dir)
            if not save_dir.exists():
                save_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions by creating a test file
            test_file = save_dir / ".test_write_permission"
            test_file.touch()
            test_file.unlink()  # Remove the test file
            
            config["save_dir"] = str(save_dir)
            save_config(config)
            console.print(f"[green]Save directory updated to: {save_dir}[/green]")
        except Exception as e:
            console.print(f"[red]Error setting save directory: {str(e)}[/red]")
            console.print(f"[yellow]Using default directory: {DEFAULT_SAVE_DIR}[/yellow]")
            config["save_dir"] = str(DEFAULT_SAVE_DIR)
            save_config(config)

def main() -> None:
    """Main function."""
    console.print(Panel.fit("[bold cyan]Instagram DM Fetcher - Fixed Version[/bold cyan]", subtitle="Fetch and save your Instagram DMs with enhanced error handling"))
    
    setup_config_dir()
    
    try:
        # Display main menu
        choices = [
            "1. Fetch direct messages",
            "2. Configure save directory",
            "3. Configure credential storage",
            "4. Manage saved credentials",
            "5. Exit"
        ]
        
        while True:
            console.print("\n[bold]Main Menu:[/bold]")
            for choice in choices:
                console.print(choice)
            
            option = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5"], default="1")
            
            if option == "1":
                # Original flow to fetch messages
                client = login_to_instagram()
                
                while True:
                    try:
                        threads = get_conversations(client)
                        
                        if not threads:
                            console.print("[yellow]No conversations found or all conversations have problematic media.[/yellow]")
                            break
                        
                        thread = select_conversation(threads)
                        
                        count = Prompt.ask(
                            "How many messages do you want to fetch?",
                            default=str(DEFAULT_MESSAGE_COUNT)
                        )
                        
                        try:
                            count = int(count)
                            if count <= 0:
                                raise ValueError("Count must be positive")
                        except ValueError:
                            console.print("[yellow]Invalid count. Using default value.[/yellow]")
                            count = DEFAULT_MESSAGE_COUNT
                        
                        messages = fetch_messages(client, thread, count)
                        
                        if messages:
                            display_messages(thread, messages, client)
                            
                            if Confirm.ask("Do you want to save these messages to a file?"):
                                filename = save_messages_to_file(thread, messages, client)
                                console.print(f"[green]Messages saved to {filename}[/green]")
                        else:
                            console.print("[yellow]No messages were retrieved.[/yellow]")
                            console.print("[cyan]This might be due to problematic media in the conversation.[/cyan]")
                            console.print("[cyan]Try selecting a different conversation or reducing the message count.[/cyan]")
                        
                        if not Confirm.ask("Do you want to fetch messages from another conversation?"):
                            break
                            
                    except Exception as fetch_error:
                        console.print(f"[red]Error during message fetching: {str(fetch_error)}[/red]")
                        console.print("[yellow]This might be a temporary issue. Try again or select a different conversation.[/yellow]")
                        
                        if not Confirm.ask("Do you want to try again?"):
                            break
            
            elif option == "2":
                # Configure save directory
                configure_save_directory()
            
            elif option == "3":
                # Configure credential storage
                configure_credentials()
            
            elif option == "4":
                # Manage saved credentials
                manage_saved_credentials()
            
            elif option == "5":
                # Exit
                break
        
        console.print("[bold green]Thank you for using Instagram DM Fetcher![/bold green]")
    
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        console.print_exception()
        # Keep console open on error
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"[bold red]Critical error: {str(e)}[/bold red]")
        console.print_exception()
        # Keep console open on critical error
        input("\nPress Enter to exit...")