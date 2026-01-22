#!/usr/bin/env python3
"""
Instagram DM Fetcher - Command Line Interface

A professional CLI tool for fetching and saving Instagram direct messages.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from instagram_dm_saver.core import InstagramAuthenticator, MessageManager
from instagram_dm_saver.storage import AppConfig, get_config, CredentialManager, MessageExporter
from instagram_dm_saver.utils import (
    InstagramDMError,
    AuthenticationError,
    TwoFactorRequired,
    MessageFetchError,
    ConversationError,
    setup_logger,
    get_logger,
)

console = Console()


class InstagramDMCLI:
    """Command-line interface for Instagram DM Fetcher."""

    def __init__(self):
        """Initialize CLI application."""
        self.config: AppConfig = get_config()

        # Setup logging
        log_level = getattr(logging, self.config.log_level)
        self.logger = setup_logger(
            "instagram_dm_saver",
            log_level=log_level,
            log_dir=self.config.log_dir,
            console_output=False  # We use Rich for console output
        )

        self.authenticator: Optional[InstagramAuthenticator] = None
        self.message_manager: Optional[MessageManager] = None
        self.credential_manager = CredentialManager(self.config.credential_storage)

    def run(self) -> None:
        """Run the CLI application."""
        self._display_welcome()

        try:
            while True:
                choice = self._display_main_menu()

                if choice == "1":
                    self._fetch_messages_flow()
                elif choice == "2":
                    self._configure_save_directory()
                elif choice == "3":
                    self._configure_credentials()
                elif choice == "4":
                    self._manage_credentials()
                elif choice == "5":
                    self._configure_settings()
                elif choice == "6":
                    self._view_logs()
                elif choice == "7":
                    break

                console.print()  # Add spacing

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            console.print(f"[bold red]Unexpected error: {e}[/bold red]")
            console.print("[yellow]Check logs for details[/yellow]")
        finally:
            console.print("[bold green]Thank you for using Instagram DM Fetcher![/bold green]")

    def _display_welcome(self) -> None:
        """Display welcome message."""
        welcome_text = """
[bold cyan]Instagram DM Fetcher v2.0[/bold cyan]

Fetch and save your Instagram DMs with:
• Secure credential storage (keyring/encrypted file)
• Multiple export formats (TXT, JSON, CSV)
• Robust error handling for problematic media
• Rate limiting to avoid API blocks
• Professional logging and monitoring
        """
        console.print(Panel(welcome_text.strip(), title="Welcome", border_style="cyan"))

    def _display_main_menu(self) -> str:
        """
        Display main menu and get user choice.

        Returns:
            User's menu choice
        """
        console.print("\n[bold]Main Menu:[/bold]")

        options = [
            "1. Fetch direct messages",
            "2. Configure save directory",
            "3. Configure credential storage",
            "4. Manage saved credentials",
            "5. Configure settings",
            "6. View logs",
            "7. Exit"
        ]

        for option in options:
            console.print(option)

        return Prompt.ask(
            "\nSelect an option",
            choices=["1", "2", "3", "4", "5", "6", "7"],
            default="1"
        )

    def _fetch_messages_flow(self) -> None:
        """Main flow for fetching messages."""
        try:
            # Authenticate
            if not self.authenticator:
                self.authenticator = InstagramAuthenticator(self.config)

            client = self.authenticator.login()

            self.message_manager = MessageManager(client)

            # Fetch and display conversations
            while True:
                try:
                    threads = self.message_manager.get_conversations()

                    if not threads:
                        console.print("[yellow]No conversations found.[/yellow]")
                        break

                    # Select conversation
                    thread = self.message_manager.select_conversation(threads)

                    # Get message count
                    count_str = Prompt.ask(
                        "How many messages do you want to fetch?",
                        default=str(self.config.default_message_count)
                    )

                    try:
                        count = int(count_str)
                        if count <= 0:
                            raise ValueError("Count must be positive")
                    except ValueError:
                        console.print("[yellow]Invalid count. Using default value.[/yellow]")
                        count = self.config.default_message_count

                    # Fetch messages
                    messages = self.message_manager.fetch_messages(thread, count)

                    if messages:
                        # Display messages
                        self.message_manager.display_messages(thread, messages, client)

                        # Save to file
                        if Confirm.ask("\nDo you want to save these messages to a file?", default=True):
                            self._save_messages(thread, messages, client)
                    else:
                        console.print("[yellow]No messages were retrieved.[/yellow]")

                    # Continue or exit
                    if not Confirm.ask("\nDo you want to fetch messages from another conversation?", default=False):
                        break

                except (MessageFetchError, ConversationError) as e:
                    console.print(f"[red]Error: {e}[/red]")
                    if not Confirm.ask("Do you want to try again?", default=True):
                        break

        except AuthenticationError as e:
            console.print(f"[bold red]Authentication failed: {e}[/bold red]")
            self.logger.error(f"Authentication failed: {e}")
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")
            self.logger.error(f"Error in fetch flow: {e}", exc_info=True)

    def _save_messages(self, thread, messages, client) -> None:
        """
        Save messages to file.

        Args:
            thread: DirectThread object
            messages: List of DirectMessage objects
            client: Instagram client
        """
        # Choose format
        format_options = {
            "1": "TXT - Plain text file (human readable)",
            "2": "JSON - Structured data format",
            "3": "CSV - Spreadsheet compatible format"
        }

        console.print("\n[bold]Choose file format:[/bold]")
        for key, value in format_options.items():
            console.print(f"{key}. {value}")

        format_choice = Prompt.ask("Select format", choices=["1", "2", "3"], default="1")
        format_map = {"1": "txt", "2": "json", "3": "csv"}
        file_format = format_map[format_choice]

        try:
            exporter = MessageExporter(self.config.save_dir)
            output_path = exporter.export(
                thread,
                messages,
                format=file_format,
                current_user_id=client.user_id,
                current_username=client.username if hasattr(client, 'username') else "You"
            )

            console.print(f"[green]Messages saved to:[/green] {output_path}")
            self.logger.info(f"Saved {len(messages)} messages to {output_path}")

        except Exception as e:
            console.print(f"[red]Failed to save messages: {e}[/red]")
            self.logger.error(f"Failed to save messages: {e}", exc_info=True)

    def _configure_save_directory(self) -> None:
        """Configure save directory."""
        console.print(f"\n[bold]Current save directory:[/bold] [cyan]{self.config.save_dir}[/cyan]")

        if Confirm.ask("Do you want to change the save directory?"):
            new_dir = Prompt.ask("Enter new save directory path", default=str(self.config.save_dir))

            try:
                new_path = Path(new_dir)
                new_path.mkdir(parents=True, exist_ok=True)

                # Test write permissions
                test_file = new_path / ".test_write"
                test_file.touch()
                test_file.unlink()

                self.config.save_dir = new_path
                self.config.save()

                console.print(f"[green]Save directory updated to: {new_path}[/green]")
                self.logger.info(f"Save directory changed to {new_path}")

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[yellow]Save directory not changed[/yellow]")

    def _configure_credentials(self) -> None:
        """Configure credential storage method."""
        method_names = {
            "keyring": "System Keyring (Most Secure)",
            "file": "Encrypted File Storage",
            "env": "Environment Variables Only",
            "none": "No Storage (Always Ask)"
        }

        current = self.config.credential_storage
        console.print(f"\n[bold]Current method:[/bold] [cyan]{method_names[current]}[/cyan]")

        if Confirm.ask("Do you want to change the credential storage method?"):
            console.print("\n[bold]Available methods:[/bold]")
            console.print("1. System Keyring (Recommended - Most Secure)")
            console.print("2. Encrypted File Storage (Portable)")
            console.print("3. Environment Variables Only")
            console.print("4. No Storage (Always Ask)")

            choice = Prompt.ask("Select method", choices=["1", "2", "3", "4"], default="1")

            method_map = {
                "1": "keyring",
                "2": "file",
                "3": "env",
                "4": "none"
            }

            new_method = method_map[choice]
            self.config.credential_storage = new_method
            self.config.save()

            console.print(f"[green]Credential storage method updated to: {method_names[new_method]}[/green]")
            self.logger.info(f"Credential storage changed to {new_method}")

    def _manage_credentials(self) -> None:
        """Manage saved credentials."""
        creds = self.credential_manager.load_credentials()

        if creds:
            console.print(f"\n[bold]Saved credentials found for:[/bold] [cyan]{creds['username']}[/cyan]")

            if Confirm.ask("Do you want to delete these credentials?"):
                if self.credential_manager.delete_credentials(creds.get('username')):
                    console.print("[green]Credentials deleted successfully[/green]")
                    self.logger.info("User deleted saved credentials")
                else:
                    console.print("[yellow]Failed to delete credentials[/yellow]")
        else:
            console.print("[yellow]No saved credentials found[/yellow]")

    def _configure_settings(self) -> None:
        """Configure application settings."""
        console.print("\n[bold cyan]Application Settings[/bold cyan]\n")

        # Display current settings
        table = Table(title="Current Settings")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Default Message Count", str(self.config.default_message_count))
        table.add_row("Batch Size", str(self.config.batch_size))
        table.add_row("Max Retries", str(self.config.max_retries))
        table.add_row("Rate Limit (calls/min)", f"{self.config.rate_limit_calls}/{self.config.rate_limit_window}s")
        table.add_row("Default Export Format", self.config.default_export_format)
        table.add_row("Log Level", self.config.log_level)

        console.print(table)

        if Confirm.ask("\nDo you want to modify settings?"):
            console.print("\n[yellow]Tip: Press Enter to keep current value[/yellow]\n")

            # Message count
            new_count = Prompt.ask(
                "Default message count (1-10000)",
                default=str(self.config.default_message_count)
            )
            try:
                self.config.default_message_count = int(new_count)
            except ValueError:
                console.print("[yellow]Invalid value, keeping current[/yellow]")

            # Log level
            console.print("\nLog levels: DEBUG, INFO, WARNING, ERROR, CRITICAL")
            new_level = Prompt.ask(
                "Log level",
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                default=self.config.log_level
            )
            self.config.log_level = new_level

            # Save
            self.config.save()
            console.print("\n[green]Settings saved successfully[/green]")
            self.logger.info("User updated application settings")

    def _view_logs(self) -> None:
        """View recent log entries."""
        log_file = self.config.log_dir / "instagram_dm_saver.log"

        if not log_file.exists():
            console.print("[yellow]No log file found[/yellow]")
            return

        try:
            # Read last N lines
            num_lines = int(Prompt.ask("How many log lines to display?", default="50"))

            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-num_lines:]

            console.print(f"\n[bold]Last {len(recent_lines)} log entries:[/bold]\n")

            for line in recent_lines:
                # Color code by log level
                if "ERROR" in line or "CRITICAL" in line:
                    console.print(f"[red]{line.strip()}[/red]")
                elif "WARNING" in line:
                    console.print(f"[yellow]{line.strip()}[/yellow]")
                elif "INFO" in line:
                    console.print(f"[green]{line.strip()}[/green]")
                else:
                    console.print(line.strip())

            console.print(f"\n[cyan]Full log file: {log_file}[/cyan]")

        except Exception as e:
            console.print(f"[red]Error reading log file: {e}[/red]")


def main() -> None:
    """Main entry point for CLI application."""
    try:
        cli = InstagramDMCLI()
        cli.run()
    except Exception as e:
        console.print(f"[bold red]Fatal error: {e}[/bold red]")
        console.print("[yellow]Please report this issue on GitHub[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
