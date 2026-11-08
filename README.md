# InstaDM Saver

Save your Instagram direct messages to a TXT, JSON or CSV file, straight from the terminal.

Everything lives in one file: `instadm_saver.py`.

## How to use

1. Install [Python](https://www.python.org/downloads/) 3.9 or newer (on Windows, tick "Add Python to PATH").
2. Double-click `instadm_saver.py`, or run `python instadm_saver.py`.

The first time, it asks whether it may install the two libraries it needs: `instagrapi` (talks to Instagram) and `rich` (the terminal interface). Say yes and it installs the newest versions for you.

On every start it checks for updates to both and installs them automatically. Instagram changes things often and `instagrapi` follows quickly, so this keeps login working. If you're offline, it skips the check and uses what's installed.

## What it does

- Logs in with your username and password (2FA and security codes are supported).
- Remembers your session, so you don't have to log in every time. Your password is never stored.
- Lists your conversations; pick one by number or search by username.
- Fetches as many messages as you want and saves them as TXT, JSON or CSV.

## "Your version of Instagram is out of date"

Instagram sometimes blocks password logins from tools like this and shows that message (it can also mean a wrong password). Choose **Browser cookie** at login instead. The app shows you how to copy the `sessionid` cookie from instagram.com in your browser.

## Where files go

- Saved chats: `~/Instagram_DM_Fetcher_Chats/<username>/` (changeable in the menu)
- Login session and settings: `~/.instagram_dm_fetcher/`

Use "Log out" in the menu to delete the saved session.

## Disclaimer

For personal use only. You are responsible for following Instagram's Terms of Service. Use at your own risk.

## License

MIT, see [LICENSE](LICENSE).
