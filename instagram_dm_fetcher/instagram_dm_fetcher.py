import os
import json
import getpass
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

# Initialize Rich console for better output
console = Console()

# Constants
CONFIG_DIR = Path.home() / ".instagram_dm_fetcher"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
SESSION_FILE = CONFIG_DIR / "session.json"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_MESSAGE_COUNT = 1000
DEFAULT_SAVE_DIR = Path.home() / "Instagram_DM_Fetcher_Chats"

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
    return {"save_dir": str(DEFAULT_SAVE_DIR)}

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

def load_credentials() -> Dict[str, str]:
    """Load saved credentials from file or .env."""
    load_dotenv()
    username = os.getenv("IG_USERNAME")
    password = os.getenv("IG_PASSWORD")
    
    if username and password:
        return {"username": username, "password": password}
    
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                credentials = json.load(f)
                return credentials
        except (json.JSONDecodeError, KeyError):
            console.print("[yellow]Credentials file is invalid.[/yellow]")
    
    return {}

def save_credentials(username: str, password: str) -> None:
    """Save credentials to file."""
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump({"username": username, "password": password}, f)
    console.print("[green]Credentials saved.[/green]")

def login_to_instagram() -> Client:
    """Log in to Instagram and return a client."""
    client = Client()
    
    if SESSION_FILE.exists():
        try:
            console.print("Attempting to load saved session...")
            client.load_settings(SESSION_FILE)
            client.get_timeline_feed()  # Test if session is valid
            console.print("[green]Successfully loaded session.[/green]")
            return client
        except Exception as e:
            console.print(f"[yellow]Failed to load session: {str(e)}[/yellow]")
    
    credentials = load_credentials()
    
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
        if Confirm.ask("Save credentials for future use?"):
            save_credentials(username, password)
        
        return client
    except Exception as e:
        console.print(f"[red]Login failed: {str(e)}[/red]")
        raise

def get_conversations(client: Client) -> List[DirectThread]:
    """Get all conversations."""
    with Progress() as progress:
        task = progress.add_task("[cyan]Fetching conversations...", total=1)
        threads = client.direct_threads()
        progress.update(task, advance=1)
    
    return threads

def display_conversations(threads: List[DirectThread]) -> None:
    """Display all conversations in a table."""
    table = Table(title="Instagram Conversations")
    
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("User(s)", style="green")
    table.add_column("Last Message", style="white")
    
    for i, thread in enumerate(threads, 1):
        users = ", ".join([user.username for user in thread.users])
        if thread.messages and hasattr(thread.messages[0], 'text'):
            last_msg = thread.messages[0].text if thread.messages[0].text is not None else "[No text content]"
        else:
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

def fetch_messages(client: Client, thread: DirectThread, count: int = DEFAULT_MESSAGE_COUNT) -> List[DirectMessage]:
    """Fetch messages from a conversation."""
    with Progress() as progress:
        task = progress.add_task(f"[cyan]Fetching {count} messages...", total=1)
        messages = client.direct_messages(thread.id, count)
        progress.update(task, advance=1)
    
    return messages

def display_messages(thread: DirectThread, messages: List[DirectMessage], client_user_id: int) -> None:
    """Display messages in a readable format."""
    usernames = {user.pk: user.username for user in thread.users}
    usernames[client_user_id] = "You"
    
    sorted_messages = sorted(messages, key=lambda m: m.timestamp)
    
    console.print(Panel(f"[bold]Conversation with {', '.join(u.username for u in thread.users)}[/bold]"))
    
    for msg in sorted_messages:
        sender = usernames.get(msg.user_id, f"Unknown ({msg.user_id})")
        timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        if msg.user_id == client_user_id:
            console.print(f"[cyan]{timestamp}[/cyan] [bold blue]{sender}:[/bold blue] {msg.text}")
        else:
            console.print(f"[cyan]{timestamp}[/cyan] [bold green]{sender}:[/bold green] {msg.text}")
        
        # Display media if present
        if msg.media and msg.media.media_type == 1:  # Image
            console.print(f"[italic][Image: {msg.media.thumbnail_url}][/italic]")
        elif msg.media and msg.media.media_type == 2:  # Video
            console.print(f"[italic][Video: {msg.media.video_url}][/italic]")

def save_messages_to_file(thread: DirectThread, messages: List[DirectMessage], client_user_id: int) -> str:
    """Save messages to a file and return the filename."""
    import datetime
    import re
    
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
            
        filename = save_folder / f"{safe_username}_{current_time}.txt"
        
        username_map = {user.pk: user.username for user in thread.users}
        username_map[client_user_id] = "You"
        
        sorted_messages = sorted(messages, key=lambda m: m.timestamp)
        
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
                
                if msg.media and msg.media.media_type == 1:  # Image
                    f.write(f"[Image: {msg.media.thumbnail_url}]\n")
                elif msg.media and msg.media.media_type == 2:  # Video
                    f.write(f"[Video: {msg.media.video_url}]\n")
                
                f.write("\n")
                
        return str(filename)
        
    except Exception as e:
        console.print(f"[bold red]Error saving messages: {str(e)}[/bold red]")
        # Create a default fallback file in the user's home directory
        fallback_file = Path.home() / f"instagram_messages_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(fallback_file, "w", encoding="utf-8") as f:
                f.write(f"Conversation with {', '.join(usernames) if 'usernames' in locals() else 'unknown'}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Error occurred while saving original file: {str(e)}\n")
                # Try to save at least some message content
                if 'sorted_messages' in locals() and sorted_messages:
                    for msg in sorted_messages[:10]:  # Save at least first 10 messages
                        f.write(f"{msg.timestamp.strftime('%H:%M:%S')} - {msg.text or '[No text content]'}\n\n")
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
    console.print(Panel.fit("[bold cyan]Instagram DM Fetcher[/bold cyan]", subtitle="Fetch and save your Instagram DMs"))
    
    setup_config_dir()
    
    try:
        # Display main menu
        choices = [
            "1. Fetch direct messages",
            "2. Configure save directory",
            "3. Exit"
        ]
        
        while True:
            console.print("\n[bold]Main Menu:[/bold]")
            for choice in choices:
                console.print(choice)
            
            option = Prompt.ask("\nSelect an option", choices=["1", "2", "3"], default="1")
            
            if option == "1":
                # Original flow to fetch messages
                client = login_to_instagram()
                
                while True:
                    threads = get_conversations(client)
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
                    display_messages(thread, messages, client.user_id)
                    
                    if Confirm.ask("Do you want to save these messages to a file?"):
                        filename = save_messages_to_file(thread, messages, client.user_id)
                        console.print(f"[green]Messages saved to {filename}[/green]")
                    
                    if not Confirm.ask("Do you want to fetch messages from another conversation?"):
                        break
            
            elif option == "2":
                # Configure save directory
                configure_save_directory()
            
            elif option == "3":
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