# Instagram DM Saver v2.0

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Professional tool for fetching and saving Instagram direct messages with enterprise-grade features.

---

## What's New in v2.0

### Major Improvements

- **Modular Architecture** - Completely refactored codebase with separated modules
- **Enhanced Security** - Encrypted credential storage using cryptography
- **Professional Logging** - Rotating log files with multiple severity levels
- **Rate Limiting** - Automatic API throttling to prevent Instagram blocks
- **Type Safety** - Full type hints throughout the codebase
- **Test Coverage** - Comprehensive pytest test suite
- **Configuration Management** - Pydantic-based configuration with validation
- **Multiple Export Formats** - Export to TXT, JSON, and CSV formats
- **Modern Interfaces** - Both GUI and CLI applications with Rich formatting

---

## Features

### Core Features

- **Secure Authentication**
  - Username/password login with 2FA support
  - Session persistence to avoid repeated logins
  - Multiple credential storage backends (system keyring, encrypted file, environment variables)

- **Message Fetching**
  - Fetch unlimited messages from any conversation
  - Robust error handling for problematic media
  - Batch fetching with progress tracking
  - Automatic retry on failures

- **Export Options**
  - **TXT**: Human-readable plain text with timestamps and date separators
  - **JSON**: Structured data format with full metadata
  - **CSV**: Spreadsheet-compatible format for data analysis

- **Security**
  - Encrypted credential storage using Fernet symmetric encryption
  - System keyring integration (macOS Keychain, Windows Credential Manager, Linux Secret Service)
  - No plaintext passwords stored anywhere
  - Secure session management

- **Performance**
  - Rate limiting to prevent API blocks (configurable, default 10 calls/60s)
  - Batch message fetching for efficiency
  - Efficient media metadata handling
  - Automatic cleanup of problematic content

- **Monitoring**
  - Professional logging framework with rotating files
  - Separate error logs for debugging
  - Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Log rotation (10MB max per file, keeps 5 backups)

---

## Installation

### Option 1: Install from Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/yyyutakaaa/InstaDM-Saver.git
cd InstaDM-Saver

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Option 2: Install via pip (when published)

```bash
pip install instagram-dm-saver
```

---

## Quick Start

### GUI Application (Recommended for Beginners)

The GUI provides a modern, user-friendly interface for managing your Instagram DMs.

```bash
# Run with system Python (recommended for macOS)
/opt/homebrew/bin/python3.11 instagram_dm_saver/gui.py

# Or if installed
instagram-dm-saver-gui
# Short alias:
igdm-gui
```

**GUI Features:**
- Modern dark theme interface
- Live chat view with message bubbles
- Real-time conversation search
- One-click message fetching
- Easy export to multiple formats
- Visual settings panel

### CLI Application (For Advanced Users)

The CLI provides a fast, terminal-based interface perfect for automation.

```bash
# Run the CLI application
instagram-dm-saver
# Short alias:
igdm
```

**CLI Features:**
- Lightning fast terminal interface
- Perfect for automation and scripting
- Rich formatted output with tables
- Full configuration control
- Progress bars and status indicators

### Python API Usage

```python
from instagram_dm_saver import (
    InstagramAuthenticator,
    MessageManager,
    MessageExporter,
    get_config
)

# Load configuration
config = get_config()

# Authenticate
authenticator = InstagramAuthenticator(config)
client = authenticator.login()

# Fetch conversations
manager = MessageManager(client)
threads = manager.get_conversations()

# Select a conversation
thread = threads[0]

# Fetch messages
messages = manager.fetch_messages(thread, count=1000)

# Export messages
exporter = MessageExporter(config.save_dir)
output_path = exporter.export(
    thread,
    messages,
    format="json",
    current_user_id=client.user_id
)

print(f"Messages saved to: {output_path}")
```

---

## GUI vs CLI Comparison

| Feature | GUI | CLI |
|---------|-----|-----|
| **Ease of Use** | Excellent - Perfect for beginners | Good - Requires terminal knowledge |
| **Visual Appeal** | Modern graphical interface | Text-based only |
| **Message Preview** | Live chat bubbles with formatting | Formatted text output |
| **Speed** | Fast | Very fast |
| **Automation** | Limited | Excellent for scripts |
| **Search** | Real-time search box | Interactive prompts |

**Choose GUI if:** You want a visual interface and prefer point-and-click interactions
**Choose CLI if:** You need speed, automation, or are comfortable with terminal commands

---

## Configuration

### Configuration File

Location: `~/.instagram_dm_fetcher/config.json`

```json
{
  "config_dir": "/Users/you/.instagram_dm_fetcher",
  "save_dir": "/Users/you/Instagram_DM_Fetcher_Chats",
  "log_dir": "/Users/you/.instagram_dm_fetcher/logs",
  "credential_storage": "keyring",
  "default_message_count": 1000,
  "batch_size": 20,
  "max_retries": 3,
  "rate_limit_calls": 10,
  "rate_limit_window": 60,
  "default_export_format": "txt",
  "log_level": "INFO"
}
```

### Environment Variables

```bash
# Set credentials via environment variables (optional)
export IG_USERNAME="your_username"
export IG_PASSWORD="your_password"
```

### Credential Storage Options

1. **System Keyring** (Recommended - Most Secure)
   - macOS: Keychain
   - Windows: Credential Manager
   - Linux: Secret Service API

2. **Encrypted File**
   - Stored in `~/.instagram_dm_fetcher/credentials.enc`
   - Encrypted using Fernet symmetric encryption
   - Encryption key stored in system keyring when available

3. **Environment Variables**
   - Set `IG_USERNAME` and `IG_PASSWORD`
   - Not persistent across sessions

4. **No Storage**
   - Always prompt for credentials
   - Most secure for shared computers

---

## Project Structure

```
InstaDM-Saver/
├── instagram_dm_saver/
│   ├── __init__.py
│   ├── cli.py                  # Command-line interface
│   ├── gui.py                  # Graphical user interface
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication logic
│   │   └── messages.py        # Message fetching
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── credentials.py     # Credential storage
│   │   └── exporters.py       # File export handlers
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── exceptions.py      # Custom exceptions
│   │   ├── logger.py          # Logging setup
│   │   └── rate_limiter.py    # Rate limiting
│   └── tests/
│       ├── conftest.py        # Test fixtures
│       ├── test_config.py
│       ├── test_credentials.py
│       ├── test_exporters.py
│       └── test_rate_limiter.py
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── setup.py                   # Package setup
├── pyproject.toml            # Modern Python configuration
├── pytest.ini                # Pytest configuration
└── README.md                 # This file
```

---

## Development

### Setup Development Environment

```bash
# Clone and install with dev dependencies
git clone https://github.com/yyyutakaaa/InstaDM-Saver.git
cd InstaDM-Saver
pip install -r requirements-dev.txt
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=instagram_dm_saver

# Run specific test file
pytest instagram_dm_saver/tests/test_config.py

# Run specific test
pytest instagram_dm_saver/tests/test_config.py::test_config_creation
```

### Code Quality

```bash
# Format code with black
black instagram_dm_saver/

# Sort imports
isort instagram_dm_saver/

# Lint with flake8
flake8 instagram_dm_saver/

# Type check with mypy
mypy instagram_dm_saver/

# Run all quality checks
black instagram_dm_saver/ && isort instagram_dm_saver/ && flake8 instagram_dm_saver/ && mypy instagram_dm_saver/
```

---

## Export Formats

### TXT Format
Human-readable format with date separators and timestamps:

```
Conversation with john_doe
======================================================================

------------- Monday, January 15, 2024 -------------

14:32:15 - You: Hey, how are you?
14:32:45 - john_doe: I'm good! How about you?
14:33:10 - You: Great! Want to grab coffee?
```

### JSON Format
Structured data format for programmatic access:

```json
{
  "conversation_info": {
    "participants": ["john_doe"],
    "thread_id": "340282366841710300949128...",
    "export_time": "2024-01-15T15:30:00",
    "message_count": 150
  },
  "messages": [
    {
      "timestamp": "2024-01-15T14:32:15",
      "sender": "You",
      "sender_id": 12345,
      "text": "Hey, how are you?",
      "message_id": "msg_123",
      "media": null
    }
  ]
}
```

### CSV Format
Spreadsheet-compatible format:

```csv
Timestamp,Date,Time,Sender,Sender_ID,Message,Media_Type,Media_URL
2024-01-15T14:32:15,2024-01-15,14:32:15,You,12345,"Hey, how are you?",,
2024-01-15T14:32:45,2024-01-15,14:32:45,john_doe,67890,"I'm good! How about you?",,
```

---

## Troubleshooting

### Authentication Issues

**Problem**: Login fails with "Two-factor authentication required"
**Solution**: The application will prompt you for your 2FA code. Enter the 6-digit code from your authenticator app.

**Problem**: "Session expired" error
**Solution**: Delete the session file and log in again:
```bash
rm ~/.instagram_dm_fetcher/session.json
instagram-dm-saver
```

### Message Fetching Issues

**Problem**: "Problematic media" errors
**Solution**: The tool automatically handles this with fallback methods. If issues persist, try reducing batch size in configuration.

**Problem**: Rate limiting / API blocks
**Solution**: The tool automatically implements rate limiting. If blocked, wait 24 hours before trying again. You can adjust rate limiting in the configuration.

### Installation Issues

**Problem**: `keyring` not working on Linux
**Solution**: Install system dependencies:
```bash
# Debian/Ubuntu
sudo apt-get install python3-dbus libsecret-1-dev

# Fedora
sudo dnf install dbus-python libsecret-devel
```

**Problem**: `cryptography` build fails
**Solution**: Install build dependencies:
```bash
# macOS
brew install openssl

# Debian/Ubuntu
sudo apt-get install build-essential libssl-dev libffi-dev python3-dev

# Fedora
sudo dnf install gcc openssl-devel libffi-devel python3-devel
```

### GUI Issues

**Problem**: `ModuleNotFoundError: No module named '_tkinter'`
**Solution**: Tkinter is not installed with your Python distribution. On macOS, use Homebrew Python which includes tkinter:
```bash
# Use Homebrew Python (has tkinter built-in)
/opt/homebrew/bin/python3.11 instagram_dm_saver/gui.py

# Or install Python with tkinter support
brew install python-tk@3.11
```

**Problem**: `igdm-gui` command not found
**Solution**: Reinstall the package:
```bash
pip install -e .
```

**Problem**: GUI window doesn't open
**Solution**: Verify that tkinter is available in your Python installation:
```bash
# Test if tkinter is available
python3 -c "import tkinter"

# If the above fails, use system Python
/opt/homebrew/bin/python3.11 instagram_dm_saver/gui.py
```

**Problem**: GUI is slow or laggy
**Solution**:
- Close other resource-intensive applications
- Reduce message count when fetching (use 100-500 instead of 5000+)
- For very large message batches, consider using the CLI instead

---

## Logging

Logs are stored in `~/.instagram_dm_fetcher/logs/`:

- `instagram_dm_saver.log` - All log messages
- `instagram_dm_saver_errors.log` - Errors and critical issues only

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical issues requiring immediate attention

You can change the log level in the configuration file or via the settings menu.

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run code quality checks (`black`, `flake8`, `mypy`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Disclaimer

This tool is for personal use only. Users are responsible for complying with Instagram's Terms of Service. The authors are not responsible for any misuse or violations. Use at your own risk.

---

## Acknowledgments

- Built with [instagrapi](https://github.com/adw0rd/instagrapi) for Instagram API access
- Terminal UI powered by [Rich](https://github.com/Textualize/rich)
- GUI built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- Secure storage via [keyring](https://github.com/jaraco/keyring)
- Encryption provided by [cryptography](https://github.com/pyca/cryptography)

---

## Support

- Bug Reports: [GitHub Issues](https://github.com/yourusername/InstaDM-Saver/issues)
- Feature Requests: [GitHub Issues](https://github.com/yourusername/InstaDM-Saver/issues)
- Documentation: [README.md](README.md)

---

Made with 💜 by yyytakaaa
