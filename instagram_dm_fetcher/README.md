# Instagram DM Fetcher

A command-line tool to fetch and save direct messages from your Instagram account.

## Features

- Two-factor authentication support
- Fetch DMs from any conversation in your Instagram inbox
- Select conversations by number or search by username
- Specify how many messages to retrieve (default: 1000)
- Display messages in a readable, styled format
- Configurable save directory with automatic permissions handling
- Save messages to organized folders with timestamped filenames
- Secure credential storage with optional password saving
- Session caching to avoid frequent logins
- User-friendly main menu with configuration options
- Robust error handling with fallback mechanisms

## Installation

1. Make sure you have Python 3.7+ installed
2. Clone this repository or download the files
3. Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage

1. Run the script:

```
python instagram_dm_fetcher.py
```

2. You'll see a main menu with options:
   - **Fetch direct messages** - Access your Instagram DMs
   - **Configure save directory** - Change where message files are saved
   - **Exit** - Close the application

3. When fetching messages:
   - Log in with your Instagram credentials (or use saved credentials)
   - If two-factor authentication is enabled, enter the verification code
   - Select a conversation by number or search for a username
   - Specify how many messages you want to fetch
   - View the messages in the terminal
   - Optionally save the messages to a file

## Setting a Custom Save Directory

By default, messages are saved to `C:\Users\<username>\Instagram_DM_Fetcher_Chats\`. To change this:

1. Select "Configure save directory" from the main menu
2. Enter the path where you want to save your message files
3. The application will test if the location is writable
4. Your preference will be saved for future sessions

If the application encounters permission issues with your chosen directory, it will automatically fall back to saving in your home directory.

## Using Environment Variables

You can store your credentials in a `.env` file in the project directory:

```
IG_USERNAME=your_username
IG_PASSWORD=your_password
```

With these variables set, the application will automatically use them to log in.

## Configuration Storage

The application stores several files in `~/.instagram_dm_fetcher/`:

- `credentials.json` - Your saved Instagram credentials (if you choose to save them)
- `session.json` - Your Instagram session data for faster logins
- `config.json` - Your application preferences, including save directory

## Security Notes

- This application uses unofficial Instagram API libraries (instagrapi)
- Using unofficial APIs may violate Instagram's Terms of Service
- Your credentials are stored locally in `~/.instagram_dm_fetcher/`
- The `.gitignore` file is set up to prevent accidentally committing credentials

## Troubleshooting

- **Permission errors when saving files**: Use the "Configure save directory" option to set a location where you have write permissions
- **The console closes immediately after an error**: The application now keeps the console open so you can read error messages
- **Login issues**: The app will attempt to use stored sessions first, then saved credentials, and finally prompt for login information

## Warning

**Use at your own risk.** Instagram may temporarily or permanently ban accounts that use unofficial APIs. This tool is for educational and personal use only.