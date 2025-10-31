#!/usr/bin/env python3
"""
Instagram DM Saver - Modern GUI Application

A beautiful, modern GUI for fetching and saving Instagram DMs with all v2.0 features.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from pathlib import Path
import threading
from typing import Optional, List
from datetime import datetime

from instagram_dm_saver.core import InstagramAuthenticator, MessageManager
from instagram_dm_saver.storage import AppConfig, get_config, CredentialManager, MessageExporter
from instagram_dm_saver.utils import (
    InstagramDMError,
    AuthenticationError,
    TwoFactorRequired,
    MessageFetchError,
    ConversationError,
    get_logger,
)
from instagrapi.types import DirectThread, DirectMessage

# Configure CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

logger = get_logger(__name__)


class LoadingSpinner(ctk.CTkFrame):
    """Animated loading spinner widget."""

    def __init__(self, master, size: int = 40, line_width: int = 4, text: str = "Loading..."):
        super().__init__(master, fg_color="transparent")
        self.size = size
        self.line_width = line_width

        self.canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            highlightthickness=0,
            bd=0,
            bg="#2b2b2b",
        )
        self.canvas.pack()

        self.label = ctk.CTkLabel(self, text=text, font=ctk.CTkFont(size=14))
        self.label.pack(pady=(5, 0))

        self.angle = 0
        self.arc = self.canvas.create_arc(
            2, 2, size - 2, size - 2,
            start=self.angle,
            extent=300,
            style="arc",
            outline="white",
            width=line_width,
        )
        self.job = None

    def _animate(self):
        """Animate the spinner."""
        self.angle = (self.angle + 10) % 360
        self.canvas.itemconfigure(self.arc, start=self.angle)
        self.job = self.after(50, self._animate)

    def start(self):
        """Start animation."""
        if not self.job:
            self._animate()

    def stop(self):
        """Stop animation."""
        if self.job:
            self.after_cancel(self.job)
            self.job = None


class InstagramDMSaverGUI:
    """Modern GUI application for Instagram DM Saver."""

    def __init__(self):
        """Initialize the GUI application."""
        # Setup
        self.config: AppConfig = get_config()
        self.logger = get_logger(__name__)

        # Initialize components
        self.authenticator: Optional[InstagramAuthenticator] = None
        self.message_manager: Optional[MessageManager] = None
        self.credential_manager = CredentialManager(self.config.credential_storage)

        # Data
        self.threads: List[DirectThread] = []
        self.current_thread: Optional[DirectThread] = None
        self.messages: List[DirectMessage] = []

        # Create main window
        self.root = ctk.CTk()
        self.root.title("Instagram DM Saver v2.0")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)

        # Main container
        self.main_container = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_container.pack(fill="both", expand=True)

        # Show login screen
        self.show_login_screen()

        self.logger.info("GUI application initialized")

    def show_login_screen(self):
        """Display the login screen."""
        # Clear container
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Create centered login frame
        login_frame = ctk.CTkFrame(self.main_container, width=450, height=600)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")
        login_frame.pack_propagate(False)

        # Logo/Title
        title_label = ctk.CTkLabel(
            login_frame,
            text="Instagram DM Saver",
            font=ctk.CTkFont(size=36, weight="bold")
        )
        title_label.pack(pady=(60, 10))

        subtitle_label = ctk.CTkLabel(
            login_frame,
            text="v2.0 - Professional Edition",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 10))

        # Features badge
        features_text = "✓ Encrypted Credentials  ✓ Rate Limiting  ✓ Professional Logging"
        features_label = ctk.CTkLabel(
            login_frame,
            text=features_text,
            font=ctk.CTkFont(size=10),
            text_color="#4CAF50"
        )
        features_label.pack(pady=(0, 40))

        # Username entry
        self.username_entry = ctk.CTkEntry(
            login_frame,
            placeholder_text="Instagram Username",
            width=350,
            height=50,
            font=ctk.CTkFont(size=14)
        )
        self.username_entry.pack(pady=10)

        # Password entry
        self.password_entry = ctk.CTkEntry(
            login_frame,
            placeholder_text="Password",
            show="•",
            width=350,
            height=50,
            font=ctk.CTkFont(size=14)
        )
        self.password_entry.pack(pady=10)

        # 2FA frame (hidden by default)
        self.twofa_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
        self.twofa_entry = ctk.CTkEntry(
            self.twofa_frame,
            placeholder_text="2FA Code (6 digits)",
            width=350,
            height=50,
            font=ctk.CTkFont(size=14)
        )
        self.twofa_entry.pack()

        # Save credentials checkbox
        self.save_creds_var = ctk.BooleanVar(value=True)
        save_creds_check = ctk.CTkCheckBox(
            login_frame,
            text="Remember credentials (stored securely)",
            variable=self.save_creds_var,
            font=ctk.CTkFont(size=12)
        )
        save_creds_check.pack(pady=15)

        # Login button
        self.login_button = ctk.CTkButton(
            login_frame,
            text="Login",
            width=350,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.handle_login
        )
        self.login_button.pack(pady=20)

        # Loading spinner (hidden by default)
        self.login_spinner = LoadingSpinner(login_frame, text="Logging in...")

        # Load saved credentials
        self.load_saved_credentials()

        # Bind Enter key
        self.password_entry.bind("<Return>", lambda e: self.handle_login())

        self.logger.info("Login screen displayed")

    def load_saved_credentials(self):
        """Load saved credentials if available."""
        try:
            creds = self.credential_manager.load_credentials()
            if creds:
                self.username_entry.insert(0, creds.get("username", ""))
                self.password_entry.insert(0, creds.get("password", ""))
                self.logger.info("Loaded saved credentials")
        except Exception as e:
            self.logger.debug(f"No saved credentials found: {e}")

    def handle_login(self):
        """Handle the login button click."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return

        # Disable button and show loading
        self.login_button.configure(state="disabled", text="Logging in...")
        self.login_spinner.pack(pady=10)
        self.login_spinner.start()

        # Run login in thread
        thread = threading.Thread(
            target=self._login_thread,
            args=(username, password, self.save_creds_var.get())
        )
        thread.daemon = True
        thread.start()

    def _login_thread(self, username: str, password: str, save_creds: bool):
        """Login in background thread."""
        try:
            self.authenticator = InstagramAuthenticator(self.config)

            try:
                client = self.authenticator.login(
                    username=username,
                    password=password,
                    save_credentials=save_creds
                )
                self.root.after(0, self.login_success)

            except TwoFactorRequired:
                self.root.after(0, self.show_2fa_input)

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            self.root.after(0, lambda: self.login_error(str(e)))

    def show_2fa_input(self):
        """Show 2FA input field."""
        self.login_spinner.stop()
        self.login_spinner.pack_forget()
        self.twofa_frame.pack(pady=10)
        self.login_button.configure(
            state="normal",
            text="Verify 2FA",
            command=self.handle_2fa
        )
        self.twofa_entry.focus()

    def handle_2fa(self):
        """Handle 2FA verification."""
        code = self.twofa_entry.get().strip()
        if not code:
            messagebox.showerror("Error", "Please enter 2FA code")
            return

        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        self.login_button.configure(state="disabled", text="Verifying...")
        self.login_spinner.pack(pady=10)
        self.login_spinner.start()

        thread = threading.Thread(
            target=self._verify_2fa_thread,
            args=(username, password, code, self.save_creds_var.get())
        )
        thread.daemon = True
        thread.start()

    def _verify_2fa_thread(self, username: str, password: str, code: str, save_creds: bool):
        """Verify 2FA in background thread."""
        try:
            client = self.authenticator.login(
                username=username,
                password=password,
                verification_code=code,
                save_credentials=save_creds
            )
            self.root.after(0, self.login_success)
        except Exception as e:
            self.logger.error(f"2FA verification failed: {e}")
            self.root.after(0, lambda: self.login_error(str(e)))

    def login_error(self, error_msg: str):
        """Handle login error."""
        self.login_spinner.stop()
        self.login_spinner.pack_forget()
        self.login_button.configure(state="normal", text="Login")
        messagebox.showerror("Login Failed", f"Error: {error_msg}")

    def login_success(self):
        """Handle successful login."""
        self.logger.info("Login successful, showing main screen")
        self.show_main_screen()

    def show_main_screen(self):
        """Display the main application screen."""
        # Clear container
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Create header
        header = ctk.CTkFrame(self.main_container, height=70, corner_radius=0, fg_color="#1f538d")
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        # Header content
        header_label = ctk.CTkLabel(
            header,
            text="📱 Instagram DM Saver v2.0",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        header_label.pack(side="left", padx=30, pady=20)

        # Header buttons frame
        header_buttons = ctk.CTkFrame(header, fg_color="transparent")
        header_buttons.pack(side="right", padx=20)

        # Settings button
        settings_btn = ctk.CTkButton(
            header_buttons,
            text="⚙️ Settings",
            width=100,
            height=35,
            command=self.show_settings,
            fg_color="#2b5278",
            hover_color="#234567"
        )
        settings_btn.pack(side="left", padx=5)

        # Logout button
        logout_btn = ctk.CTkButton(
            header_buttons,
            text="🚪 Logout",
            width=100,
            height=35,
            command=self.logout,
            fg_color="#c62828",
            hover_color="#b71c1c"
        )
        logout_btn.pack(side="left", padx=5)

        # Create main content area with two panels
        content_frame = ctk.CTkFrame(self.main_container, corner_radius=0, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Left panel - Conversations list
        self.left_panel = ctk.CTkFrame(content_frame, width=450, corner_radius=0)
        self.left_panel.pack(side="left", fill="y", padx=0, pady=0)
        self.left_panel.pack_propagate(False)

        # Search bar
        search_frame = ctk.CTkFrame(self.left_panel, height=70, fg_color="transparent")
        search_frame.pack(fill="x", padx=15, pady=15)
        search_frame.pack_propagate(False)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Search conversations...",
            height=45,
            font=ctk.CTkFont(size=14)
        )
        self.search_entry.pack(fill="x", pady=5)
        self.search_entry.bind("<KeyRelease>", self.filter_conversations)

        # Conversations list header
        list_header = ctk.CTkFrame(self.left_panel, height=50, fg_color="#2b2b2b")
        list_header.pack(fill="x", padx=10, pady=(5, 10))
        list_header.pack_propagate(False)

        list_label = ctk.CTkLabel(
            list_header,
            text="Conversations",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        list_label.pack(side="left", padx=20, pady=10)

        refresh_btn = ctk.CTkButton(
            list_header,
            text="🔄",
            width=40,
            height=30,
            command=self.load_conversations,
            font=ctk.CTkFont(size=16)
        )
        refresh_btn.pack(side="right", padx=10)

        # Scrollable frame for conversations
        self.conv_scroll = ctk.CTkScrollableFrame(self.left_panel)
        self.conv_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Right panel - Messages view
        self.right_panel = ctk.CTkFrame(content_frame, corner_radius=0)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        # Initial message in right panel
        welcome_label = ctk.CTkLabel(
            self.right_panel,
            text="Select a conversation to view messages",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        welcome_label.place(relx=0.5, rely=0.5, anchor="center")

        # Load conversations
        self.load_conversations()

        self.logger.info("Main screen displayed")

    def load_conversations(self):
        """Load conversations in background."""
        # Show loading spinner
        for widget in self.conv_scroll.winfo_children():
            widget.destroy()

        spinner = LoadingSpinner(self.conv_scroll, text="Loading conversations...")
        spinner.pack(pady=50)
        spinner.start()

        thread = threading.Thread(target=self._load_conversations_thread)
        thread.daemon = True
        thread.start()

    def _load_conversations_thread(self):
        """Load conversations in background thread."""
        try:
            client = self.authenticator.get_client()
            if not client:
                raise AuthenticationError("Not authenticated")

            self.message_manager = MessageManager(client)
            self.threads = self.message_manager.get_conversations()

            self.logger.info(f"Loaded {len(self.threads)} conversations")
            self.root.after(0, self.display_conversations)

        except Exception as e:
            self.logger.error(f"Failed to load conversations: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Error",
                f"Failed to load conversations: {str(e)}"
            ))

    def display_conversations(self):
        """Display loaded conversations."""
        # Clear loading
        for widget in self.conv_scroll.winfo_children():
            widget.destroy()

        if not self.threads:
            no_conv_label = ctk.CTkLabel(
                self.conv_scroll,
                text="No conversations found",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_conv_label.pack(pady=50)
            return

        # Display each conversation
        for thread in self.threads:
            self.create_conversation_item(thread)

    def create_conversation_item(self, thread: DirectThread):
        """Create a conversation item widget."""
        # Frame for each conversation
        conv_frame = ctk.CTkFrame(
            self.conv_scroll,
            height=90,
            cursor="hand2",
            fg_color="#2b2b2b",
            border_width=2,
            border_color="#3b3b3b"
        )
        conv_frame.pack(fill="x", padx=5, pady=5)
        conv_frame.pack_propagate(False)

        # Username
        users = ", ".join([user.username for user in thread.users])
        name_label = ctk.CTkLabel(
            conv_frame,
            text=users,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(padx=20, pady=(20, 5), anchor="w")

        # Last message preview
        last_msg = "[No messages]"
        try:
            if thread.messages and thread.messages[0].text:
                last_msg = thread.messages[0].text
                if len(last_msg) > 60:
                    last_msg = last_msg[:57] + "..."
        except:
            pass

        msg_label = ctk.CTkLabel(
            conv_frame,
            text=last_msg,
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w"
        )
        msg_label.pack(padx=20, pady=(0, 20), anchor="w")

        # Click handler
        conv_frame.bind("<Button-1>", lambda e: self.select_conversation(thread))
        name_label.bind("<Button-1>", lambda e: self.select_conversation(thread))
        msg_label.bind("<Button-1>", lambda e: self.select_conversation(thread))

        # Hover effect
        def on_enter(e):
            conv_frame.configure(border_color="#1f538d")

        def on_leave(e):
            conv_frame.configure(border_color="#3b3b3b")

        conv_frame.bind("<Enter>", on_enter)
        conv_frame.bind("<Leave>", on_leave)

    def filter_conversations(self, event):
        """Filter conversations based on search."""
        search_term = self.search_entry.get().lower()

        # Clear current display
        for widget in self.conv_scroll.winfo_children():
            widget.destroy()

        # Display filtered conversations
        filtered_count = 0
        for thread in self.threads:
            users_str = " ".join([user.username.lower() for user in thread.users])
            if search_term in users_str:
                self.create_conversation_item(thread)
                filtered_count += 1

        if filtered_count == 0 and search_term:
            no_results_label = ctk.CTkLabel(
                self.conv_scroll,
                text=f"No conversations found for '{search_term}'",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_results_label.pack(pady=50)

    def select_conversation(self, thread: DirectThread):
        """Handle conversation selection."""
        self.current_thread = thread
        self.logger.info(f"Selected conversation: {[u.username for u in thread.users]}")
        self.show_messages_view()

    def show_messages_view(self):
        """Display messages interface for selected conversation."""
        # Clear right panel
        for widget in self.right_panel.winfo_children():
            widget.destroy()

        # Header with conversation info
        msg_header = ctk.CTkFrame(self.right_panel, height=90, fg_color="#2b5278")
        msg_header.pack(fill="x", padx=0, pady=0)
        msg_header.pack_propagate(False)

        users = ", ".join([user.username for user in self.current_thread.users])
        conv_label = ctk.CTkLabel(
            msg_header,
            text=f"💬 {users}",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        )
        conv_label.pack(side="left", padx=30, pady=25)

        # Action buttons
        button_frame = ctk.CTkFrame(msg_header, fg_color="transparent")
        button_frame.pack(side="right", padx=20, pady=25)

        # Message count selector
        count_label = ctk.CTkLabel(
            button_frame,
            text="Messages:",
            font=ctk.CTkFont(size=12),
            text_color="white"
        )
        count_label.pack(side="left", padx=5)

        self.msg_count_var = tk.StringVar(value=str(self.config.default_message_count))
        count_options = ctk.CTkOptionMenu(
            button_frame,
            values=["50", "100", "500", "1000", "5000", "10000"],
            variable=self.msg_count_var,
            width=100,
            height=35
        )
        count_options.pack(side="left", padx=5)

        # Fetch button
        fetch_btn = ctk.CTkButton(
            button_frame,
            text="📥 Fetch Messages",
            command=self.fetch_messages,
            width=140,
            height=35,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        fetch_btn.pack(side="left", padx=5)

        # Save button
        self.save_btn = ctk.CTkButton(
            button_frame,
            text="💾 Save to File",
            state="disabled",
            command=self.save_messages,
            width=120,
            height=35,
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        self.save_btn.pack(side="left", padx=5)

        # Messages area
        self.msg_scroll = ctk.CTkScrollableFrame(self.right_panel)
        self.msg_scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Info label
        info_label = ctk.CTkLabel(
            self.msg_scroll,
            text="Click 'Fetch Messages' to load conversation history",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        info_label.pack(pady=100)

    def fetch_messages(self):
        """Fetch messages for current conversation."""
        try:
            count = int(self.msg_count_var.get())
        except ValueError:
            count = self.config.default_message_count

        # Show loading
        for widget in self.msg_scroll.winfo_children():
            widget.destroy()

        spinner = LoadingSpinner(self.msg_scroll, text=f"Fetching {count} messages...")
        spinner.pack(pady=100)
        spinner.start()

        thread = threading.Thread(target=self._fetch_messages_thread, args=(count,))
        thread.daemon = True
        thread.start()

    def _fetch_messages_thread(self, count: int):
        """Fetch messages in background thread."""
        try:
            self.messages = self.message_manager.fetch_messages(
                self.current_thread,
                count
            )
            self.logger.info(f"Fetched {len(self.messages)} messages")
            self.root.after(0, self.display_messages)

        except Exception as e:
            self.logger.error(f"Failed to fetch messages: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Error",
                f"Failed to fetch messages: {str(e)}"
            ))

    def display_messages(self):
        """Display fetched messages."""
        # Clear loading
        for widget in self.msg_scroll.winfo_children():
            widget.destroy()

        if not self.messages:
            no_msg_label = ctk.CTkLabel(
                self.msg_scroll,
                text="No messages found",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_msg_label.pack(pady=100)
            return

        # Enable save button
        self.save_btn.configure(state="normal")

        # Sort messages by timestamp
        sorted_messages = sorted(self.messages, key=lambda m: m.timestamp)

        # Display messages
        current_date = None
        client = self.authenticator.get_client()

        for msg in sorted_messages:
            # Date separator
            msg_date = msg.timestamp.date()
            if current_date != msg_date:
                date_frame = ctk.CTkFrame(
                    self.msg_scroll,
                    height=40,
                    fg_color="transparent"
                )
                date_frame.pack(fill="x", pady=20)

                date_label = ctk.CTkLabel(
                    date_frame,
                    text=msg_date.strftime("%B %d, %Y"),
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="gray"
                )
                date_label.pack()
                current_date = msg_date

            # Message bubble
            is_me = msg.user_id == client.user_id

            bubble_container = ctk.CTkFrame(self.msg_scroll, fg_color="transparent")
            bubble_container.pack(fill="x", padx=20, pady=5)

            bubble = ctk.CTkFrame(
                bubble_container,
                corner_radius=15,
                fg_color="#1f538d" if is_me else "#3b3b3b"
            )

            if is_me:
                bubble.pack(side="right", padx=10, fill="x")
            else:
                bubble.pack(side="left", padx=10, fill="x")

            # Message content
            msg_text = msg.text if msg.text else "[Media]"
            msg_label = ctk.CTkLabel(
                bubble,
                text=msg_text,
                font=ctk.CTkFont(size=14),
                wraplength=500,
                anchor="w",
                justify="left"
            )
            msg_label.pack(padx=15, pady=(12, 5), anchor="w")

            # Timestamp
            time_label = ctk.CTkLabel(
                bubble,
                text=msg.timestamp.strftime("%H:%M"),
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )

            if is_me:
                time_label.pack(padx=15, pady=(0, 10), anchor="e")
            else:
                time_label.pack(padx=15, pady=(0, 10), anchor="w")

        self.logger.info(f"Displayed {len(sorted_messages)} messages")

    def save_messages(self):
        """Save messages to file."""
        if not self.messages:
            messagebox.showwarning("Warning", "No messages to save")
            return

        # Create format selection window
        format_window = ctk.CTkToplevel(self.root)
        format_window.title("Select Export Format")
        format_window.geometry("400x300")
        format_window.transient(self.root)
        format_window.grab_set()

        # Center window
        format_window.update_idletasks()
        x = (format_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (format_window.winfo_screenheight() // 2) - (300 // 2)
        format_window.geometry(f"+{x}+{y}")

        # Title
        title_label = ctk.CTkLabel(
            format_window,
            text="Choose Export Format",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=30)

        # Format variable
        format_var = tk.StringVar(value="txt")

        # Format options
        formats = [
            ("txt", "📝 TXT - Plain text file (human readable)"),
            ("json", "📊 JSON - Structured data format"),
            ("csv", "📈 CSV - Spreadsheet compatible")
        ]

        for value, text in formats:
            radio = ctk.CTkRadioButton(
                format_window,
                text=text,
                variable=format_var,
                value=value,
                font=ctk.CTkFont(size=14)
            )
            radio.pack(pady=10, padx=30, anchor="w")

        # Export button
        def do_export():
            format_window.destroy()
            self._save_messages_with_format(format_var.get())

        export_btn = ctk.CTkButton(
            format_window,
            text="Export",
            command=do_export,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        export_btn.pack(pady=30)

    def _save_messages_with_format(self, file_format: str):
        """Save messages with selected format."""
        try:
            client = self.authenticator.get_client()
            exporter = MessageExporter(self.config.save_dir)

            output_path = exporter.export(
                self.current_thread,
                self.messages,
                format=file_format,
                current_user_id=client.user_id,
                current_username=client.username if hasattr(client, 'username') else "You"
            )

            self.logger.info(f"Exported {len(self.messages)} messages to {output_path}")

            messagebox.showinfo(
                "Success",
                f"Messages saved successfully!\n\n{output_path}"
            )

        except Exception as e:
            self.logger.error(f"Failed to save messages: {e}")
            messagebox.showerror("Error", f"Failed to save messages: {str(e)}")

    def show_settings(self):
        """Show settings window."""
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("600x500")
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Center window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (600 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (500 // 2)
        settings_window.geometry(f"+{x}+{y}")

        # Title
        title_label = ctk.CTkLabel(
            settings_window,
            text="⚙️ Settings",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=30)

        # Settings frame
        settings_frame = ctk.CTkFrame(settings_window)
        settings_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))

        # Save directory
        dir_label = ctk.CTkLabel(
            settings_frame,
            text="Save Directory:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        dir_label.pack(anchor="w", padx=20, pady=(20, 5))

        dir_entry = ctk.CTkEntry(
            settings_frame,
            width=500,
            height=40
        )
        dir_entry.insert(0, str(self.config.save_dir))
        dir_entry.pack(padx=20, pady=5)

        def browse_directory():
            directory = filedialog.askdirectory()
            if directory:
                dir_entry.delete(0, tk.END)
                dir_entry.insert(0, directory)

        browse_btn = ctk.CTkButton(
            settings_frame,
            text="Browse",
            command=browse_directory,
            width=100
        )
        browse_btn.pack(padx=20, pady=10)

        # Default message count
        count_label = ctk.CTkLabel(
            settings_frame,
            text="Default Message Count:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        count_label.pack(anchor="w", padx=20, pady=(20, 5))

        count_entry = ctk.CTkEntry(
            settings_frame,
            width=200,
            height=40
        )
        count_entry.insert(0, str(self.config.default_message_count))
        count_entry.pack(padx=20, pady=5)

        # Log level
        log_label = ctk.CTkLabel(
            settings_frame,
            text="Log Level:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        log_label.pack(anchor="w", padx=20, pady=(20, 5))

        log_var = tk.StringVar(value=self.config.log_level)
        log_option = ctk.CTkOptionMenu(
            settings_frame,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            variable=log_var,
            width=200,
            height=40
        )
        log_option.pack(padx=20, pady=5)

        # Save button
        def save_settings():
            try:
                self.config.save_dir = Path(dir_entry.get())
                self.config.default_message_count = int(count_entry.get())
                self.config.log_level = log_var.get()
                self.config.save()

                self.logger.info("Settings saved")
                messagebox.showinfo("Success", "Settings saved successfully!")
                settings_window.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

        save_btn = ctk.CTkButton(
            settings_frame,
            text="Save Settings",
            command=save_settings,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        save_btn.pack(pady=30)

    def logout(self):
        """Handle logout."""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            try:
                self.authenticator.logout(delete_session=True, delete_credentials=False)
                self.authenticator = None
                self.message_manager = None
                self.threads = []
                self.current_thread = None
                self.messages = []

                self.logger.info("User logged out")
                self.show_login_screen()

            except Exception as e:
                self.logger.error(f"Error during logout: {e}")
                messagebox.showerror("Error", f"Error during logout: {str(e)}")

    def run(self):
        """Run the GUI application."""
        self.logger.info("Starting GUI application")
        self.root.mainloop()


def main():
    """Main entry point for GUI application."""
    try:
        app = InstagramDMSaverGUI()
        app.run()
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Fatal error: {e}", exc_info=True)
        messagebox.showerror("Fatal Error", f"Application crashed: {str(e)}")


if __name__ == "__main__":
    main()
