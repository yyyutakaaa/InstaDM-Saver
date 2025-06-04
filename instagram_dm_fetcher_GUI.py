import customtkinter as ctk
from customtkinter import CTkScrollableFrame
import tkinter as tk
from tkinter import messagebox
import threading
from pathlib import Path
from datetime import datetime
import json

# Import all functions from the original script
from instagram_dm_fetcher import (
    login_to_instagram,
    get_conversations,
    fetch_messages,
    save_messages_to_file,
    load_config,
    save_config,
    setup_config_dir,
    CONFIG_DIR,
    DEFAULT_SAVE_DIR,
    SESSION_FILE,
    CREDENTIALS_FILE,
)

# Configure CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class InstagramDMFetcherGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Instagram DM Fetcher")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        # Initialize variables
        self.client = None
        self.threads = []
        self.current_thread = None
        self.messages = []
        
        # Setup
        setup_config_dir()
        
        # Create main container
        self.main_container = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_container.pack(fill="both", expand=True)
        
        # Start with login screen
        self.show_login_screen()
        
    def show_login_screen(self):
        """Display the login screen."""
        # Clear container
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        # Create centered login frame
        login_frame = ctk.CTkFrame(self.main_container, width=400, height=500)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")
        login_frame.pack_propagate(False)
        
        # Logo/Title
        title_label = ctk.CTkLabel(
            login_frame, 
            text="Instagram DM Fetcher", 
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title_label.pack(pady=(50, 10))
        
        subtitle_label = ctk.CTkLabel(
            login_frame, 
            text="Secure login to your account", 
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 40))
        
        # Username entry
        self.username_entry = ctk.CTkEntry(
            login_frame, 
            placeholder_text="Username", 
            width=300, 
            height=45,
            font=ctk.CTkFont(size=14)
        )
        self.username_entry.pack(pady=10)
        
        # Password entry
        self.password_entry = ctk.CTkEntry(
            login_frame, 
            placeholder_text="Password", 
            show="•", 
            width=300, 
            height=45,
            font=ctk.CTkFont(size=14)
        )
        self.password_entry.pack(pady=10)
        
        # 2FA entry (hidden by default)
        self.twofa_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
        self.twofa_entry = ctk.CTkEntry(
            self.twofa_frame,
            placeholder_text="2FA Code",
            width=300,
            height=45,
            font=ctk.CTkFont(size=14)
        )
        self.twofa_entry.pack()
        
        # Login button
        self.login_button = ctk.CTkButton(
            login_frame,
            text="Login",
            width=300,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.handle_login
        )
        self.login_button.pack(pady=20)
        
        # Progress bar (hidden by default)
        self.login_progress = ctk.CTkProgressBar(login_frame, width=300)
        
        # Load saved credentials if available
        self.load_saved_credentials()
        
    def load_saved_credentials(self):
        """Load saved credentials if available."""
        try:
            if (CONFIG_DIR / "credentials.json").exists():
                with open(CONFIG_DIR / "credentials.json", "r") as f:
                    creds = json.load(f)
                    self.username_entry.insert(0, creds.get("username", ""))
                    self.password_entry.insert(0, creds.get("password", ""))
        except:
            pass
    
    def handle_login(self):
        """Handle the login process."""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        # Show progress
        self.login_button.configure(state="disabled", text="Logging in...")
        self.login_progress.pack(pady=10)
        self.login_progress.start()
        
        # Run login in separate thread
        thread = threading.Thread(target=self._login_thread, args=(username, password))
        thread.daemon = True
        thread.start()

    def _login_thread(self, username, password):
        """Login thread to avoid freezing UI."""
        try:
            # Try to load existing session first
            from instagram_dm_fetcher import Client, SESSION_FILE
            self.client = Client()

            if SESSION_FILE.exists():
                try:
                    self.client.load_settings(SESSION_FILE)
                    # Reuse session by calling login with stored credentials
                    self.client.login(username, password)
                    self.root.after(0, self.login_success)
                    return
                except:
                    pass
            
            # Perform login
            try:
                self.client.login(username, password)
                self.client.dump_settings(SESSION_FILE)
                self.root.after(0, self.login_success)
            except Exception as e:
                if "Two-factor authentication required" in str(e):
                    self.root.after(0, self.show_2fa_input)
                else:
                    self.root.after(0, lambda: self.login_error(str(e)))
                    
        except Exception as e:
            self.root.after(0, lambda: self.login_error(str(e)))
    
    def show_2fa_input(self):
        """Show 2FA input field."""
        self.login_progress.stop()
        self.login_progress.pack_forget()
        self.twofa_frame.pack(pady=10)
        self.login_button.configure(
            state="normal", 
            text="Verify 2FA",
            command=self.handle_2fa
        )
    
    def handle_2fa(self):
        """Handle 2FA verification."""
        code = self.twofa_entry.get()
        if not code:
            messagebox.showerror("Error", "Please enter 2FA code")
            return
        
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        self.login_button.configure(state="disabled", text="Verifying...")
        self.login_progress.pack(pady=10)
        self.login_progress.start()
        
        thread = threading.Thread(
            target=self._verify_2fa_thread, 
            args=(username, password, code)
        )
        thread.daemon = True
        thread.start()
    
    def _verify_2fa_thread(self, username, password, code):
        """Verify 2FA in separate thread."""
        try:
            self.client.login(username, password, verification_code=code)
            self.client.dump_settings(SESSION_FILE)
            self.root.after(0, self.login_success)
        except Exception as e:
            self.root.after(0, lambda: self.login_error(str(e)))
    
    def login_error(self, error_msg):
        """Handle login error."""
        self.login_progress.stop()
        self.login_progress.pack_forget()
        self.login_button.configure(state="normal", text="Login")
        messagebox.showerror("Login Failed", f"Error: {error_msg}")
    
    def login_success(self):
        """Handle successful login."""
        self.show_main_screen()
    
    def show_main_screen(self):
        """Display the main application screen."""
        # Clear container
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        # Create header
        header = ctk.CTkFrame(self.main_container, height=60, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        # Header content
        header_label = ctk.CTkLabel(
            header,
            text="Instagram DM Fetcher",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header_label.pack(side="left", padx=20, pady=15)
        
        # Settings button
        settings_btn = ctk.CTkButton(
            header,
            text="⚙️ Settings",
            width=100,
            command=self.show_settings
        )
        settings_btn.pack(side="right", padx=20, pady=15)
        
        # Logout button
        logout_btn = ctk.CTkButton(
            header,
            text="Logout",
            width=100,
            command=self.logout
        )
        logout_btn.pack(side="right", padx=10, pady=15)
        
        # Create main content area with two panels
        content_frame = ctk.CTkFrame(self.main_container, corner_radius=0)
        content_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Left panel - Conversations list
        self.left_panel = ctk.CTkFrame(content_frame, width=400, corner_radius=0)
        self.left_panel.pack(side="left", fill="y", padx=0, pady=0)
        self.left_panel.pack_propagate(False)
        
        # Search bar
        search_frame = ctk.CTkFrame(self.left_panel, height=60)
        search_frame.pack(fill="x", padx=10, pady=10)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Search conversations...",
            height=40
        )
        self.search_entry.pack(fill="x", padx=10, pady=10)
        self.search_entry.bind("<KeyRelease>", self.filter_conversations)
        
        # Conversations list
        list_label = ctk.CTkLabel(
            self.left_panel,
            text="Conversations",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        list_label.pack(padx=20, pady=(10, 5), anchor="w")
        
        # Scrollable frame for conversations
        self.conv_scroll = CTkScrollableFrame(self.left_panel)
        self.conv_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Right panel - Messages view
        self.right_panel = ctk.CTkFrame(content_frame, corner_radius=0)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=0, pady=0)
        
        # Load conversations
        self.load_conversations()
    
    def load_conversations(self):
        """Load conversations in background."""
        # Show loading
        loading_label = ctk.CTkLabel(
            self.conv_scroll,
            text="Loading conversations...",
            font=ctk.CTkFont(size=14)
        )
        loading_label.pack(pady=20)
        
        thread = threading.Thread(target=self._load_conversations_thread)
        thread.daemon = True
        thread.start()
    
    def _load_conversations_thread(self):
        """Load conversations in separate thread."""
        try:
            self.threads = get_conversations(self.client)
            self.root.after(0, self.display_conversations)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load conversations: {str(e)}"))
    
    def display_conversations(self):
        """Display loaded conversations."""
        # Clear loading message
        for widget in self.conv_scroll.winfo_children():
            widget.destroy()
        
        # Display each conversation
        for i, thread in enumerate(self.threads):
            self.create_conversation_item(thread, i)
    
    def create_conversation_item(self, thread, index):
        """Create a conversation item widget."""
        # Frame for each conversation
        conv_frame = ctk.CTkFrame(
            self.conv_scroll,
            height=80,
            cursor="hand2"
        )
        conv_frame.pack(fill="x", padx=5, pady=5)
        conv_frame.pack_propagate(False)
        
        # Store thread reference
        conv_frame.thread = thread
        conv_frame.index = index
        
        # Username
        users = ", ".join([user.username for user in thread.users])
        name_label = ctk.CTkLabel(
            conv_frame,
            text=users,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(padx=15, pady=(15, 5), anchor="w")
        
        # Last message preview
        if thread.messages and thread.messages[0].text:
            last_msg = thread.messages[0].text[:50] + "..." if len(thread.messages[0].text) > 50 else thread.messages[0].text
        else:
            last_msg = "[No messages]"
        
        msg_label = ctk.CTkLabel(
            conv_frame,
            text=last_msg,
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w"
        )
        msg_label.pack(padx=15, pady=(0, 15), anchor="w")
        
        # Click handler
        conv_frame.bind("<Button-1>", lambda e: self.select_conversation(thread, index))
        name_label.bind("<Button-1>", lambda e: self.select_conversation(thread, index))
        msg_label.bind("<Button-1>", lambda e: self.select_conversation(thread, index))
    
    def filter_conversations(self, event):
        """Filter conversations based on search."""
        search_term = self.search_entry.get().lower()
        
        # Clear current display
        for widget in self.conv_scroll.winfo_children():
            widget.destroy()
        
        # Display filtered conversations
        for i, thread in enumerate(self.threads):
            users_str = " ".join([user.username.lower() for user in thread.users])
            if search_term in users_str:
                self.create_conversation_item(thread, i)
    
    def select_conversation(self, thread, index):
        """Handle conversation selection."""
        self.current_thread = thread
        self.show_messages_view()
    
    def show_messages_view(self):
        """Display messages for selected conversation."""
        # Clear right panel
        for widget in self.right_panel.winfo_children():
            widget.destroy()
        
        # Header with conversation info
        msg_header = ctk.CTkFrame(self.right_panel, height=80)
        msg_header.pack(fill="x", padx=0, pady=0)
        msg_header.pack_propagate(False)
        
        users = ", ".join([user.username for user in self.current_thread.users])
        conv_label = ctk.CTkLabel(
            msg_header,
            text=users,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        conv_label.pack(side="left", padx=20, pady=25)
        
        # Action buttons
        button_frame = ctk.CTkFrame(msg_header, fg_color="transparent")
        button_frame.pack(side="right", padx=20, pady=25)
        
        # Message count selector
        count_label = ctk.CTkLabel(button_frame, text="Messages:")
        count_label.pack(side="left", padx=5)
        
        self.msg_count_var = tk.StringVar(value="100")
        count_options = ctk.CTkOptionMenu(
            button_frame,
            values=["50", "100", "500", "1000", "5000"],
            variable=self.msg_count_var,
            width=100
        )
        count_options.pack(side="left", padx=5)
        
        # Fetch button
        fetch_btn = ctk.CTkButton(
            button_frame,
            text="Fetch Messages",
            command=self.fetch_messages
        )
        fetch_btn.pack(side="left", padx=5)
        
        # Save button
        self.save_btn = ctk.CTkButton(
            button_frame,
            text="Save to File",
            state="disabled",
            command=self.save_messages
        )
        self.save_btn.pack(side="left", padx=5)
        
        # Messages area
        self.msg_scroll = CTkScrollableFrame(self.right_panel)
        self.msg_scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Info label
        info_label = ctk.CTkLabel(
            self.msg_scroll,
            text="Click 'Fetch Messages' to load conversation",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        info_label.pack(pady=50)
    
    def fetch_messages(self):
        """Fetch messages for current conversation."""
        count = int(self.msg_count_var.get())
        
        # Show loading
        for widget in self.msg_scroll.winfo_children():
            widget.destroy()
        
        loading_label = ctk.CTkLabel(
            self.msg_scroll,
            text=f"Fetching {count} messages...",
            font=ctk.CTkFont(size=14)
        )
        loading_label.pack(pady=50)
        
        progress = ctk.CTkProgressBar(self.msg_scroll, width=300)
        progress.pack(pady=10)
        progress.start()
        
        thread = threading.Thread(target=self._fetch_messages_thread, args=(count,))
        thread.daemon = True
        thread.start()
    
    def _fetch_messages_thread(self, count):
        """Fetch messages in separate thread."""
        try:
            self.messages = fetch_messages(self.client, self.current_thread, count)
            self.root.after(0, self.display_messages)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch messages: {str(e)}"))
    
    def display_messages(self):
        """Display fetched messages."""
        # Clear loading
        for widget in self.msg_scroll.winfo_children():
            widget.destroy()
        
        # Enable save button
        self.save_btn.configure(state="normal")
        
        # Sort messages by timestamp
        sorted_messages = sorted(self.messages, key=lambda m: m.timestamp)
        
        # Display messages
        current_date = None
        for msg in sorted_messages:
            # Date separator
            msg_date = msg.timestamp.date()
            if current_date != msg_date:
                date_frame = ctk.CTkFrame(self.msg_scroll, height=40, fg_color="transparent")
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
            is_me = msg.user_id == self.client.user_id
            
            bubble_frame = ctk.CTkFrame(self.msg_scroll, fg_color="transparent")
            bubble_frame.pack(fill="x", padx=20, pady=5, anchor="e" if is_me else "w")
            
            bubble = ctk.CTkFrame(
                bubble_frame,
                corner_radius=15,
                fg_color="#1f538d" if is_me else "#2b2b2b"
            )
            bubble.pack(side="right" if is_me else "left", padx=10)
            
            # Message content
            msg_text = msg.text if msg.text else "[Media]"
            msg_label = ctk.CTkLabel(
                bubble,
                text=msg_text,
                font=ctk.CTkFont(size=14),
                wraplength=400,
                anchor="w",
                justify="left"
            )
            msg_label.pack(padx=15, pady=10)
            
            # Timestamp
            time_label = ctk.CTkLabel(
                bubble,
                text=msg.timestamp.strftime("%H:%M"),
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            time_label.pack(padx=15, pady=(0, 5), anchor="e" if is_me else "w")
    
    def save_messages(self):
        """Save messages to file."""
        if not self.messages:
            messagebox.showwarning("Warning", "No messages to save")
            return
        
        try:
            filename = save_messages_to_file(
                self.current_thread,
                self.messages,
                self.client.user_id
            )
            messagebox.showinfo("Success", f"Messages saved to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save messages: {str(e)}")
    
    def show_settings(self):
        """Show settings window."""
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x300")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Title
        title_label = ctk.CTkLabel(
            settings_window,
            text="Settings",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Save directory setting
        config = load_config()
        current_dir = config.get("save_dir", str(DEFAULT_SAVE_DIR))
        
        dir_frame = ctk.CTkFrame(settings_window)
        dir_frame.pack(fill="x", padx=30, pady=20)
        
        dir_label = ctk.CTkLabel(
            dir_frame,
            text="Save Directory:",
            font=ctk.CTkFont(size=14)
        )
        dir_label.pack(anchor="w", padx=10, pady=5)
        
        self.dir_entry = ctk.CTkEntry(
            dir_frame,
            height=40,
            font=ctk.CTkFont(size=12)
        )
        self.dir_entry.pack(fill="x", padx=10, pady=5)
        self.dir_entry.insert(0, current_dir)
        
        # Browse button
        browse_btn = ctk.CTkButton(
            dir_frame,
            text="Browse",
            width=100,
            command=self.browse_directory
        )
        browse_btn.pack(pady=10)
        
        # Save button
        save_settings_btn = ctk.CTkButton(
            settings_window,
            text="Save Settings",
            command=lambda: self.save_settings(settings_window)
        )
        save_settings_btn.pack(pady=20)
    
    def browse_directory(self):
        """Browse for directory."""
        from tkinter import filedialog
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
    
    def save_settings(self, window):
        """Save settings."""
        new_dir = self.dir_entry.get()
        
        try:
            # Test if directory is valid
            save_dir = Path(new_dir)
            if not save_dir.exists():
                save_dir.mkdir(parents=True, exist_ok=True)
            
            config = {"save_dir": str(save_dir)}
            save_config(config)
            messagebox.showinfo("Success", "Settings saved successfully")
            window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def logout(self):
        """Handle logout."""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            # Remove saved session so the next launch requires login again
            try:
                if SESSION_FILE.exists():
                    SESSION_FILE.unlink()
            except Exception as e:
                messagebox.showwarning("Warning", f"Failed to remove session file: {e}")

            # Remove stored credentials if present
            try:
                if CREDENTIALS_FILE.exists():
                    CREDENTIALS_FILE.unlink()
            except Exception as e:
                messagebox.showwarning("Warning", f"Failed to remove credentials file: {e}")

            self.client = None
            self.threads = []
            self.current_thread = None
            self.messages = []
            self.show_login_screen()
    
    def run(self):
        """Run the application."""
        self.root.mainloop()

if __name__ == "__main__":
    app = InstagramDMFetcherGUI()
    app.run()
