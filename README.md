# Instagram DM Fetcher

Fetch & save your Instagram DMs — **now available in both GUI and CLI versions**!

---

## 🚀 Features

* **Secure login** with username, password, and 2FA support
* **Fetch DMs** from your entire inbox
* **Search, select & filter** conversations by username
* **Save messages** as organized, timestamped text files
* **User-friendly interface**: choose between a modern GUI or a fast CLI

---

## 🖥️ GUI Version

A sleek, easy-to-use desktop application. No terminal required—everything works with a click.

### Getting Started

1. **Clone the repository** (if you haven’t already):

   ```bash
   git clone https://github.com/yourusername/InstaDM-Saver.git
   cd InstaDM-Saver/InstaDM-Saver
   ```

2. **Create and activate a virtual environment** (optional but recommended):

   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the GUI application**:

   ```bash
   python instagram_dm_fetcher_GUI.py
   ```

5. **Use the App**:

   * Enter your Instagram credentials and log in (2FA if enabled)
   * Browse your conversations list on the left
   * Select a conversation to view messages
   * Choose how many messages to fetch and click "Fetch Messages"
   * Click "Save to File" to export DMs as a text file

> **Note:** If you’re on Windows and want a standalone executable, use the `.exe` in the `dist` folder—no Python install needed! See the "Build as .exe" section below.

---

## ⚡ CLI Version

For power users who prefer a quick, no-frills command-line experience.

### Getting Started

1. **Clone the repository** (if you haven’t already):

   ```bash
   git clone https://github.com/yourusername/InstaDM-Saver.git
   cd InstaDM-Saver/InstaDM-Saver
   ```

2. **Create and activate a virtual environment** (optional but recommended):

   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the CLI script**:

   ```bash
   python instagram_dm_fetcher.py
   ```

5. **Follow the prompts**:

   * Enter your Instagram username and password
   * (Optional) Enter 2FA if prompted
   * View a numbered list of conversations
   * Enter the number corresponding to the conversation you want
   * Enter how many messages to fetch
   * DMs will be saved as a timestamped text file in the default folder (`saved_messages/`) or a custom folder if configured

---

## 📦 Build as .exe (Windows Only)

If you’d like a single-file Windows executable for the GUI version, follow these steps:

1. **Make sure you have a clean Python 3.11 (or 3.10) installation** (PyInstaller compatibility)

2. **Navigate to the project folder** in a terminal and create/activate a virtual environment (if not already):

   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   ```

3. **Install PyInstaller and all other dependencies**:

   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

4. **Build the .exe**:

   ```bash
   .\venv\Scripts\pyinstaller.exe \
     --noconfirm \
     --onefile \
     --windowed \
     --name InstagramDMFetcher \
     instagram_dm_fetcher_GUI.py
   ```

5. **Find your executable**:

   * The single `.exe` file will appear in the `dist/` folder as `InstagramDMFetcher.exe`
   * Double-click to run without needing Python installed

6. **(Optional) Clean up build artifacts**:

   ```bash
   # In the project root:
   rmdir /s /q build
   rmdir /s /q dist\InstagramDMFetcher
   del InstagramDMFetcher.spec
   del build.log
   ```

---

## ⚙️ Configuration & Saved Files

* **Configuration directory**: On first run, a `config/` folder is created next to the script. It stores:

  * `credentials.json` (encrypted Instagram username/password)
  * `settings.json` (e.g., custom save directory)
  * `session.json` (Instagram session tokens to avoid frequent logins)

* **Saved DMs**: By default, all downloaded messages are saved under `saved_messages/` in the project folder. Each conversation gets its own subfolder named after the participants, with timestamped `.txt` files.

> You can change the save directory in the GUI under **Settings → Save Directory** or by editing `config/settings.json` directly.

---

## 📜 Requirements

Listed in `requirements.txt`:

```
customtkinter
python-dotenv
rich
instagrapi
pillow
```

Install all at once with:

```bash
pip install -r requirements.txt
```

---

## 💬 Troubleshooting

* **"No module named '...'?"** Make sure you installed requirements and activated your venv.
* **Build errors with PyInstaller**: Use Python 3.11 or 3.10 to avoid compatibility issues.
* **Instagram login fails (2FA, checkpoints)**: Make sure your credentials and app verification code are correct. Check your network connection and try again.
* **GUI .exe crashes on startup**: Verify that you built it on the same Python version and installed all dependencies.

For more help, open an issue on GitHub or contact me directly.

---

## 📚 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙌 Acknowledgments

* Built with ❤️ using `instagrapi` for Instagram API access
* UI powered by [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
* Icons & design inspiration from various open-source projects

---

Enjoy fetching those DMs!
