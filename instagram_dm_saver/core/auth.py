"""Authentication and session management for Instagram."""

from pathlib import Path
from typing import Optional, Dict
import getpass

from instagrapi import Client
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress

from ..storage.config import AppConfig
from ..storage.credentials import CredentialManager
from ..utils.exceptions import AuthenticationError, TwoFactorRequired
from ..utils.logger import get_logger
from ..utils.rate_limiter import instagram_rate_limiter

logger = get_logger(__name__)
console = Console()


class InstagramAuthenticator:
    """Handle Instagram authentication and session management."""

    def __init__(self, config: AppConfig):
        """
        Initialize authenticator.

        Args:
            config: Application configuration
        """
        self.config = config
        self.credential_manager = CredentialManager(config.credential_storage)
        self.client: Optional[Client] = None

    @instagram_rate_limiter
    def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verification_code: Optional[str] = None,
        save_credentials: bool = True
    ) -> Client:
        """
        Login to Instagram with session persistence.

        Args:
            username: Instagram username (optional, will load from storage or prompt)
            password: Instagram password (optional, will load from storage or prompt)
            verification_code: 2FA verification code (if required)
            save_credentials: Whether to save credentials after successful login

        Returns:
            Authenticated Instagram client

        Raises:
            AuthenticationError: If login fails
        """
        self.client = Client()

        # Try to load existing session
        session_file = self.config.get_session_file()
        if session_file.exists():
            try:
                # We use a simple status spinner here to avoid blocking UI perception
                with console.status("[cyan]Loading saved session...[/cyan]"):
                    logger.info("Attempting to load saved session...")
                    self.client.load_settings(session_file)

                    # Get credentials for session validation
                    if not username or not password:
                        creds = self.credential_manager.load_credentials()
                        if creds:
                            username = creds.get("username")
                            password = creds.get("password")

                    if username and password:
                        self.client.login(username, password)
                        logger.info("Successfully loaded existing session")
                        console.print("[green]Successfully loaded session.[/green]")
                        return self.client
                    else:
                        # Try to verify session without login
                        self.client.get_timeline_feed()
                        logger.info("Session is still valid")
                        console.print("[green]Session is still valid.[/green]")
                        return self.client

            except Exception as e:
                logger.warning(f"Failed to load saved session: {e}")
                console.print(f"[yellow]Failed to load saved session (will try fresh login): {e}[/yellow]")
                # Continue with fresh login

        # Get credentials if not provided
        if not username or not password:
            creds = self._get_credentials()
            username = creds["username"]
            password = creds["password"]
        
        # Helper to perform the actual login call
        def attempt_login(u, p, code=None):
             with console.status("[cyan]Logging in to Instagram... (this may take a minute)[/cyan]", spinner="dots"):
                if code:
                    self.client.login(u, p, verification_code=code)
                else:
                    self.client.login(u, p)

        # Perform login
        try:
            try:
                attempt_login(username, password, verification_code)
            except Exception as e:
                error_msg = str(e)
                if "two-factor authentication" in error_msg.lower() or "2fa" in error_msg.lower():
                    logger.warning("Two-factor authentication required")
                    console.print("[yellow]Two-factor authentication required[/yellow]")
                    
                    # Ask for code immediately
                    code = Prompt.ask("Enter the verification code from your authenticator app")
                    
                    # Retry login with code
                    attempt_login(username, password, code)
                else:
                    raise e
            
            logger.info(f"Successfully logged in as {username}")
            console.print("[green]Login successful![/green]")

            # Save session
            try:
                self.client.dump_settings(session_file)
                logger.info(f"Session saved to {session_file}")
            except Exception as e:
                logger.warning(f"Failed to save session file: {e}")

            # Save credentials if requested
            if save_credentials:
                # auto-save if we looked them up, or ask?
                # The original logic asked. Let's keep asking but maybe smarter.
                # If we loaded from cred manager, no need to ask again unless changed?
                # Simplifying: just ask if the user hasn't saved them before / manual entry
                if Confirm.ask("Save credentials for future use?", default=True):
                    self.credential_manager.save_credentials(username, password)

            return self.client

        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise AuthenticationError(f"Login failed: {e}")

    def login_with_2fa(
        self,
        username: str,
        password: str,
        save_credentials: bool = True
    ) -> Client:
        """
        Login with 2FA support (prompts for code).

        Args:
            username: Instagram username
            password: Instagram password
            save_credentials: Whether to save credentials

        Returns:
            Authenticated Instagram client

        Raises:
            AuthenticationError: If login fails
        """
        try:
            # First try without 2FA
            return self.login(username, password, save_credentials=save_credentials)

        except TwoFactorRequired:
            console.print("[yellow]Two-factor authentication required[/yellow]")
            verification_code = Prompt.ask("Enter the verification code from your authenticator app")

            return self.login(
                username,
                password,
                verification_code=verification_code,
                save_credentials=save_credentials
            )

    def _get_credentials(self) -> Dict[str, str]:
        """
        Get credentials from storage or user input.

        Returns:
            Dict with username and password
        """
        # Try to load saved credentials
        creds = self.credential_manager.load_credentials()
        if creds:
            console.print(f"[cyan]Using saved credentials for {creds['username']}[/cyan]")
            return creds

        # Prompt for credentials
        console.print("[yellow]No saved credentials found.[/yellow]")
        username = Prompt.ask("Enter your Instagram username")
        password = getpass.getpass("Enter your Instagram password: ")

        return {"username": username, "password": password}

    def logout(self, delete_session: bool = True, delete_credentials: bool = False) -> None:
        """
        Logout and optionally delete session/credentials.

        Args:
            delete_session: Whether to delete saved session
            delete_credentials: Whether to delete saved credentials
        """
        try:
            if delete_session:
                session_file = self.config.get_session_file()
                if session_file.exists():
                    session_file.unlink()
                    logger.info("Session file deleted")
                    console.print("[green]Session deleted.[/green]")

            if delete_credentials:
                # Need username for keyring deletion
                if self.client:
                    username = self.client.username
                    self.credential_manager.delete_credentials(username)
                else:
                    console.print("[yellow]Could not delete credentials (no active session)[/yellow]")

            self.client = None
            logger.info("Logged out successfully")

        except Exception as e:
            logger.error(f"Error during logout: {e}")
            console.print(f"[yellow]Error during logout: {e}[/yellow]")

    def get_client(self) -> Optional[Client]:
        """
        Get current authenticated client.

        Returns:
            Instagram client or None if not authenticated
        """
        return self.client

    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self.client is not None
