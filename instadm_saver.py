#!/usr/bin/env python3
"""
InstaDM Saver - fetch and save your Instagram direct messages.

Double-click this file (or run `python instadm_saver.py`).
The first time it runs, it asks to install the two libraries it needs
(instagrapi to talk to Instagram, rich for the terminal UI).
"""

import copy
import csv
import importlib
import json
import os
import re
import site
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

APP_NAME = "InstaDM Saver"
APP_DIR = Path.home() / ".instagram_dm_fetcher"
SESSION_FILE = APP_DIR / "session.json"
SETTINGS_FILE = APP_DIR / "settings.json"
DEFAULT_SAVE_DIR = Path.home() / "Instagram_DM_Fetcher_Chats"
DEFAULT_COUNT = 1000

REQUIREMENTS = [
    # (import name, pip name, what it's for)
    ("instagrapi", "instagrapi", "talks to Instagram"),
    ("rich", "rich", "the pretty terminal interface"),
]

# Instagram gradient
PURPLE, MAGENTA, PINK, RED, ORANGE, YELLOW = "#833AB4", "#C13584", "#E1306C", "#FD1D1D", "#F77737", "#FCAF45"
GRADIENT = [PURPLE, MAGENTA, PINK, RED, ORANGE, YELLOW]
MUTED, FAINT, GOOD, BAD = "grey58", "grey35", "#7EE787", "#FF6B6B"

if os.name == "nt":
    os.system("")  # turns on ANSI colors in the classic Windows console

# Windows consoles can choke on emoji in messages; never crash on printing.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# --------------------------------------------------------------------------
# Colors without rich (used before rich is installed)
# --------------------------------------------------------------------------

def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _blend(stops, t):
    """Color at position t (0..1) along a list of hex stops."""
    t = min(max(t, 0.0), 1.0) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    a, b = _rgb(stops[i]), _rgb(stops[i + 1])
    f = t - i
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


def _ansi(hex_or_rgb, text, bold=False):
    r, g, b = _rgb(hex_or_rgb) if isinstance(hex_or_rgb, str) else hex_or_rgb
    return f"\x1b[{'1;' if bold else ''}38;2;{r};{g};{b}m{text}\x1b[0m"


def _ansi_gradient(text, bold=True):
    n = max(len(text) - 1, 1)
    return "".join(_ansi(_blend(GRADIENT, i / n), ch, bold) for i, ch in enumerate(text))


# --------------------------------------------------------------------------
# First-run setup: ask, then install
# --------------------------------------------------------------------------

def _missing_requirements():
    # find_spec checks without importing, so pip can still replace the files afterwards.
    import importlib.util
    return [(pip_name, why) for module, pip_name, why in REQUIREMENTS
            if importlib.util.find_spec(module) is None]


def _installed_versions():
    from importlib import metadata
    versions = {}
    for _, pip_name, _ in REQUIREMENTS:
        try:
            versions[pip_name] = metadata.version(pip_name)
        except metadata.PackageNotFoundError:
            versions[pip_name] = None
    return versions


def _pip_install(names, label, timeout=None):
    """pip install --upgrade, falling back to a --user install. Returns (ok, output)."""
    base = [sys.executable, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check", *names]
    ok, out = _run_with_spinner(base, label, timeout)
    if not ok:
        ok, out = _run_with_spinner(base + ["--user"], "retrying as user install", timeout)
    return ok, out


def _report_versions(before, after):
    for name, new in after.items():
        old = before.get(name)
        if old is None and new:
            print(f"    {_ansi(PINK, '•', True)} {_ansi('#ffffff', name, True)} {_ansi('#999999', new)}")
        elif old != new and new:
            print(f"    {_ansi(PINK, '↑', True)} {_ansi('#ffffff', name, True)} "
                  f"{_ansi('#999999', old)} {_ansi('#666666', '→')} {_ansi(GOOD, new, True)}")


def check_for_updates():
    """Runs on every start: update instagrapi and rich if a newer version exists."""
    names = [p for _, p, _ in REQUIREMENTS]
    before = _installed_versions()
    print()
    ok, _ = _pip_install(names, "checking for updates", timeout=90)
    if not ok:
        print(f"    {_ansi('#999999', 'could not check right now (offline?), using the installed versions')}")
        time.sleep(1.2)
        return
    after = _installed_versions()
    if after == before:
        print(f"    {_ansi('#999999', 'everything is up to date')}")
        time.sleep(0.5)
    else:
        _report_versions(before, after)
        time.sleep(1.5)


def _run_with_spinner(cmd, label, timeout=None):
    """Run a command quietly while showing a little spinner. Returns (ok, output)."""
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    result = {}

    def worker():
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               errors="replace", timeout=timeout)
            result["code"], result["out"] = p.returncode, p.stdout
        except Exception as e:  # timeout or pip missing
            result["code"], result["out"] = 1, str(e)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    i = 0
    while t.is_alive():
        sys.stdout.write(f"\r  {_ansi(_blend(GRADIENT, (i % 20) / 19), frames[i % len(frames)], True)} "
                         f"{_ansi('#bbbbbb', label)}   ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    ok = result.get("code") == 0
    mark = _ansi(GOOD, "✓", True) if ok else _ansi(BAD, "✗", True)
    sys.stdout.write(f"\r  {mark} {_ansi('#bbbbbb', label)}   \n")
    return ok, result.get("out", "")


def ensure_requirements():
    missing = _missing_requirements()
    if not missing:
        check_for_updates()
        return

    width = 58
    line = lambda s="", raw=None: print(  # noqa: E731
        "  " + _ansi(MAGENTA, "│") + "  " + s + " " * (width - 3 - len(raw if raw is not None else s))
        + _ansi(MAGENTA, "│"))

    print()
    print("  " + _ansi_gradient(f"✦ {APP_NAME} ✦"))
    print()
    print("  " + _ansi(MAGENTA, "╭" + "─" * (width - 1) + "╮"))
    line(_ansi("#ffffff", "First time setup", True), "First time setup")
    line()
    line("To run, this app needs:")
    for pip_name, why in missing:
        raw = f"  • {pip_name:<11} {why}"
        line(f"  {_ansi(PINK, '•', True)} {_ansi('#ffffff', f'{pip_name:<11}', True)} {_ansi('#999999', why)}", raw)
    line()
    line("They're installed with pip, in their newest version.")
    line("On every start the app checks for updates by itself.")
    print("  " + _ansi(MAGENTA, "╰" + "─" * (width - 1) + "╯"))
    print()

    answer = input(f"  {_ansi(PINK, '›', True)} Install now? {_ansi('#888888', '(Y/n)')} ").strip().lower()
    if answer not in ("", "y", "yes", "j", "ja"):
        names = " ".join(p for p, _ in missing)
        print()
        print(f"  {_ansi('#bbbbbb', 'No problem. You can install them yourself later with:')}")
        print(f"  {_ansi(YELLOW, f'python -m pip install {names}')}")
        raise SystemExit(0)

    print()
    if subprocess.call([sys.executable, "-m", "pip", "--version"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
        _run_with_spinner([sys.executable, "-m", "ensurepip", "--upgrade"], "setting up pip")

    # Install what's missing and update what's already there, all to the newest version.
    names = [p for p, _ in missing]
    all_names = [p for _, p, _ in REQUIREMENTS]
    before = _installed_versions()
    ok, out = _pip_install(all_names, f"installing {', '.join(names)} (newest versions)")
    if ok:
        _report_versions(before, _installed_versions())
    if not ok:
        print()
        print("  " + _ansi(BAD, "Installation failed. Last lines from pip:", True))
        for l in out.strip().splitlines()[-8:]:
            print("    " + _ansi("#999999", l))
        print(f"\n  Try it yourself: {_ansi(YELLOW, 'python -m pip install ' + ' '.join(names))}")
        raise SystemExit(1)

    # A fresh --user install isn't on sys.path yet in this process.
    try:
        site.addsitedir(site.getusersitepackages())
    except Exception:
        pass
    importlib.invalidate_caches()
    time.sleep(0.4)


# --------------------------------------------------------------------------
# UI (rich)
# --------------------------------------------------------------------------

console = None  # set in init_ui() once rich is available


def init_ui():
    global console
    import logging
    logging.disable(logging.CRITICAL)  # instagrapi prints raw tracebacks otherwise
    from rich.console import Console
    console = Console(highlight=False)


LETTERS = {
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "S": ["███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"],
    "T": ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "],
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "D": ["██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "],
    "M": ["███╗   ███╗", "████╗ ████║", "██╔████╔██║", "██║╚██╔╝██║", "██║ ╚═╝ ██║", "╚═╝     ╚═╝"],
}


def gradient(text, stops=GRADIENT, bold=True, offset=0.0):
    from rich.text import Text
    out = Text()
    n = max(len(text) - 1, 1)
    for i, ch in enumerate(text):
        r, g, b = _blend(stops, (i / n + offset) % 1.0001)
        out.append(ch, style=f"{'bold ' if bold else ''}#{r:02x}{g:02x}{b:02x}")
    return out


def header(state):
    from rich.align import Align
    from rich.text import Text

    console.clear()
    console.print()
    word = "INSTADM"
    rows = ["".join(LETTERS[c][i] for c in word) for i in range(6)]
    if console.width >= len(rows[0]) + 4:
        for row in rows:
            console.print(Align.center(gradient(row)))
    else:
        console.print(Align.center(gradient("I N S T A D M")))
    console.print(Align.center(Text("s  a  v  e  r", style=f"bold {MUTED}")))
    console.print()

    status = Text()
    client = state.get("client")
    if client is not None:
        status.append("● ", style=f"bold {GOOD}")
        status.append(f"@{client.username}", style="bold white")
    else:
        status.append("○ ", style=FAINT)
        status.append("not logged in", style=MUTED)
    status.append("   ·   ", style=FAINT)
    status.append("saving to ", style=MUTED)
    status.append(str(save_dir(state["settings"])), style=PINK)
    console.print(Align.center(status))
    console.print()

    notice = state.pop("notice", None)
    if notice:
        kind, msg = notice
        color, mark = {"ok": (GOOD, "✓"), "err": (BAD, "✗"), "info": (YELLOW, "›")}[kind]
        console.print(Align.center(Text.assemble((f"{mark} ", f"bold {color}"), (msg, color))))
        console.print()


def pill(key, color=PINK):
    from rich.text import Text
    return Text(f" {key} ", style=f"bold white on {color}")


def panel(body, title=None, color=MAGENTA, width=None, padding=(1, 3)):
    from rich import box
    from rich.panel import Panel
    return Panel(body, title=f"[bold {color}] {title} [/]" if title else None, title_align="left",
                 border_style=color, box=box.ROUNDED, padding=padding, width=width)


def centered(renderable):
    from rich.align import Align
    console.print(Align.center(renderable))


def say(msg, kind="info"):
    color, mark = {"ok": (GOOD, "✓"), "err": (BAD, "✗"), "info": (PINK, "›"), "dim": (FAINT, "·")}[kind]
    console.print(f"  [bold {color}]{mark}[/] [{MUTED if kind == 'dim' else 'white'}]{msg}[/]")


def error_box(title, msg):
    from rich.text import Text
    console.print()
    centered(panel(Text(str(msg), style="white"), title=title, color=BAD, width=min(70, console.width - 4)))


def ask(label, default=None, password=False):
    hint = f" [{FAINT}]({default})[/]" if default not in (None, "") else ""
    answer = console.input(f"  [bold {PINK}]›[/] [bold white]{label}[/]{hint} ", password=password).strip()
    return answer if answer else (default if default is not None else "")


def ask_yes(label, default=True):
    hint = "Y/n" if default else "y/N"
    answer = console.input(f"  [bold {PINK}]›[/] [bold white]{label}[/] [{FAINT}]({hint})[/] ").strip().lower()
    return default if not answer else answer in ("y", "yes", "j", "ja")


def ask_choice(label, choices, default):
    while True:
        answer = ask(label, default)
        if answer in choices:
            return answer
        say(f"choose one of {', '.join(choices)}", "err")


def spinner(text):
    return console.status(f"[{MUTED}]{text}[/]", spinner="dots12", spinner_style=f"bold {PINK}")


# --------------------------------------------------------------------------
# Settings and small helpers
# --------------------------------------------------------------------------

def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(settings):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def save_dir(settings):
    return Path(settings.get("save_dir") or DEFAULT_SAVE_DIR)


def safe_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def media_info(msg):
    """Return (kind, url) for image/video messages, else (None, None)."""
    try:
        media = getattr(msg, "media", None)
        kind = getattr(media, "media_type", None)
        if kind == 1:
            return "Image", str(getattr(media, "thumbnail_url", "") or "")
        if kind == 2:
            return "Video", str(getattr(media, "video_url", "") or "")
    except Exception:
        pass
    return None, None


# --------------------------------------------------------------------------
# Login
# --------------------------------------------------------------------------

def login(state):
    from instagrapi import Client
    from instagrapi.exceptions import TwoFactorRequired

    settings = state["settings"]
    APP_DIR.mkdir(parents=True, exist_ok=True)
    client = Client()
    client.delay_range = [1, 3]
    live = {}

    def code_handler(username, choice):
        if live.get("status"):
            live["status"].stop()
        return ask(f"Instagram sent a security code via {choice}. Code")

    client.challenge_code_handler = code_handler

    # Reuse a saved session so you don't have to log in every time.
    if SESSION_FILE.exists():
        try:
            with spinner("restoring your session"):
                client.load_settings(SESSION_FILE)
                client.get_timeline_feed()
            say(f"welcome back, [bold]@{client.username}[/]", "ok")
            return client
        except Exception:
            say("saved session expired, please log in again", "dim")
            uuids = client.get_settings().get("uuids")
            client.set_settings({})
            if uuids:
                client.set_uuids(uuids)

    from rich.table import Table
    grid = Table.grid(padding=(0, 2))
    grid.add_column()
    grid.add_column(style="bold white")
    grid.add_column(style=MUTED)
    grid.add_row(pill(1, PURPLE), "Username + password", "the normal way")
    grid.add_row(pill(2, PINK), "Browser cookie", "use this if option 1 fails")
    console.print()
    centered(panel(grid, title="log in", width=min(64, console.width - 4)))
    console.print()
    method = ask_choice("how do you want to log in", ["1", "2"], "1")

    if method == "1":
        try:
            username = password_login(client, settings, live, TwoFactorRequired)
        except Exception as e:
            error_box("login failed", explain_login_error(e))
            if not ask_yes("try logging in with a browser cookie instead?", True):
                raise LoginCancelled()
            client = fresh_client(client)
            username = cookie_login(client)
    else:
        username = cookie_login(client)

    client.dump_settings(SESSION_FILE)
    settings["username"] = username
    save_settings(settings)
    say(f"logged in as [bold]@{username}[/]", "ok")
    return client


class LoginCancelled(Exception):
    """User chose to stop logging in; go back to the menu quietly."""


def fresh_client(old):
    from instagrapi import Client
    client = Client()
    client.delay_range = [1, 3]
    try:
        client.set_uuids(old.get_settings().get("uuids") or {})
    except Exception:
        pass
    return client


def explain_login_error(e):
    text = str(e)
    if "out of date" in text.lower() or "upgrade" in text.lower():
        return (f"Instagram said: \"{text}\"\n\n"
                "This usually isn't about your app version. Instagram blocks password logins from tools "
                "like this for some accounts, and it also shows this message for a wrong password.\n\n"
                "Logging in with a browser cookie almost always works.")
    if "password" in text.lower():
        return f"Instagram said: \"{text}\"\n\nDouble-check your password, or log in with a browser cookie."
    return f"Instagram said: \"{text}\""


def password_login(client, settings, live, TwoFactorRequired):
    username = ask("username", settings.get("username")).lstrip("@")
    password = ask("password", password=True)

    def attempt(code=None):
        with spinner("logging in, this can take a moment") as status:
            live["status"] = status
            if code:
                client.login(username, password, verification_code=code)
            else:
                client.login(username, password)

    try:
        attempt()
    except Exception as e:
        text = str(e).lower()
        if not (isinstance(e, TwoFactorRequired) or "two-factor" in text or "2fa" in text):
            raise
        say("two-factor authentication is on", "info")
        attempt(ask("6-digit code (SMS or authenticator app)"))
    return username


def cookie_login(client):
    from rich.text import Text
    steps = Text.assemble(
        ("Copy your login cookie from the browser\n\n", "bold white"),
        ("1  ", f"bold {PINK}"), ("Open ", MUTED), ("instagram.com", "bold white"),
        (" in Chrome/Edge and make sure you're logged in\n", MUTED),
        ("2  ", f"bold {PINK}"), ("Press ", MUTED), ("F12", "bold white"), (" and go to the ", MUTED),
        ("Application", "bold white"), (" tab\n", MUTED),
        ("   ", ""), ("(Firefox: ", FAINT), ("Storage", FAINT), (")\n", FAINT),
        ("3  ", f"bold {PINK}"), ("Click ", MUTED), ("Cookies › https://www.instagram.com\n", "bold white"),
        ("4  ", f"bold {PINK}"), ("Find ", MUTED), ("sessionid", f"bold {ORANGE}"),
        (" and copy its value\n\n", MUTED),
        ("Treat it like a password: it gives access to your account.", f"italic {FAINT}"),
    )
    console.print()
    centered(panel(steps, title="browser cookie", color=PINK, width=min(72, console.width - 4)))
    console.print()

    while True:
        raw = ask("paste sessionid (hidden)", password=True)
        sessionid = raw.strip().strip('"').strip("'").replace("sessionid=", "").replace(":", "%3A")
        if not sessionid:
            raise LoginCancelled()
        try:
            with spinner("checking your session"):
                client.login_by_sessionid(sessionid)
            return client.username
        except Exception:
            say("Instagram didn't accept that sessionid. Copy it again, or leave empty to stop", "err")


# --------------------------------------------------------------------------
# Cleaning raw API data that instagrapi's models sometimes reject
# --------------------------------------------------------------------------

TS_LIMIT = 253402300799  # year 9999 in seconds


def _normalize_ts(value):
    try:
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        if isinstance(value, (int, float)):
            n = int(value)
            for _ in range(2):  # micro/milliseconds -> seconds
                if n <= TS_LIMIT:
                    break
                n //= 1000
            return min(n, TS_LIMIT)
    except Exception:
        pass
    return value


def _normalize_timestamps(data):
    if isinstance(data, dict):
        for key, value in list(data.items()):
            data[key] = _normalize_timestamps(value)
            if "timestamp" in key and isinstance(data[key], (int, float, str)):
                data[key] = _normalize_ts(data[key])
    elif isinstance(data, list):
        return [_normalize_timestamps(item) for item in data]
    return data


def clean_item(item):
    if not isinstance(item, dict):
        return item
    try:
        cleaned = _normalize_timestamps(copy.deepcopy(item))
        clip = cleaned.get("clip")
        if isinstance(clip, dict) and "clip" in clip:
            clip = clip["clip"]
        meta = clip.get("clips_metadata") if isinstance(clip, dict) else None
        if isinstance(meta, dict):
            sound = meta.get("original_sound_info")
            if "original_sound_info" in meta and not isinstance(sound, dict):
                sound = meta["original_sound_info"] = {}
            if isinstance(sound, dict):
                for k, v in {"audio_id": "", "original_audio_title": "", "progressive_download_url": "",
                             "dash_manifest": "", "duration_in_ms": 0, "is_explicit": False}.items():
                    sound.setdefault(k, v)
                artist = sound.get("ig_artist")
                if not isinstance(artist, dict):
                    sound["ig_artist"] = {"username": "", "pk": 0}
                else:
                    artist.setdefault("username", "")
                    artist.setdefault("pk", 0)
            for field in ("music_info", "template_info"):
                if field in meta and meta[field] is None:
                    del meta[field]
        return cleaned
    except Exception:
        return None


# --------------------------------------------------------------------------
# Conversations and messages
# --------------------------------------------------------------------------

def get_conversations(client):
    from instagrapi.extractors import extract_direct_thread

    with spinner("loading your inbox"):
        for limit in (5, 1, 0):
            try:
                return client.direct_threads(thread_message_limit=limit)
            except Exception:
                continue

        # Last resort: raw API call and clean each thread ourselves.
        result = client.private_request("direct_v2/inbox/", params={"visual_message_return_type": "unseen"})
        threads, skipped = [], 0
        for data in (result or {}).get("inbox", {}).get("threads", []):
            try:
                data = copy.deepcopy(data)
                data["items"] = [c for c in (clean_item(i) for i in data.get("items", [])[:20]) if c]
                threads.append(extract_direct_thread(data))
            except Exception:
                skipped += 1
    if skipped:
        say(f"skipped {skipped} chat(s) that couldn't be read", "dim")
    return threads


def thread_name(thread):
    names = [u.username for u in thread.users]
    return ", ".join(names) if names else (getattr(thread, "thread_title", None) or "unknown")


def show_inbox(threads):
    from rich import box
    from rich.table import Table
    from rich.text import Text

    table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {MAGENTA}", border_style=FAINT,
                  show_edge=False, pad_edge=False, expand=True)
    table.add_column("#", justify="right", style=f"bold {PINK}", width=4)
    table.add_column("chat", style="bold white", no_wrap=True, ratio=2)
    table.add_column("last message", style=MUTED, no_wrap=True, overflow="ellipsis", ratio=3)

    for i, t in enumerate(threads, 1):
        preview = ""
        try:
            if t.messages:
                m = t.messages[0]
                preview = m.text or ("▣ media" if getattr(m, "media", None) else "")
        except Exception:
            pass
        name = Text("@" + thread_name(t)) if len(t.users) == 1 else Text(thread_name(t))
        table.add_row(str(i), name, preview.replace("\n", " "))

    console.print()
    centered(panel(table, title=f"inbox · {len(threads)} chats", width=min(90, console.width - 2),
                   padding=(0, 2)))
    console.print()


def pick_conversation(threads):
    while True:
        choice = ask("pick a chat by number, or type a name to search", "1").lstrip("@")
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(threads):
                return threads[idx]
            say("that number isn't in the list", "err")
            continue

        matches = [t for t in threads if any(choice.lower() in u.username.lower() for u in t.users)]
        if len(matches) == 1:
            say(f"found [bold]@{thread_name(matches[0])}[/]", "ok")
            return matches[0]
        if not matches:
            say("no chat matches that name", "err")
            continue
        for i, t in enumerate(matches, 1):
            console.print("    ", pill(i, MAGENTA), f" [white]{thread_name(t)}[/]")
        sub = ask("which one", "1")
        if sub.isdigit() and 1 <= int(sub) <= len(matches):
            return matches[int(sub) - 1]


def fetch_messages(client, thread, count):
    try:
        with spinner(f"fetching up to {count:,} messages from @{thread_name(thread)}"):
            return client.direct_messages(thread.id, count)
    except Exception:
        say("some messages have unusual media, switching to safe mode", "dim")
    return fetch_messages_safe(client, thread.id, count)


def fetch_messages_safe(client, thread_id, count):
    """Fetch in small batches via the raw API, skipping messages that won't parse."""
    from instagrapi.extractors import extract_direct_message
    from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

    messages, cursor, failures, batch = [], None, 0, 20
    progress = Progress(SpinnerColumn("dots12", style=f"bold {PINK}"),
                        TextColumn(f"[{MUTED}]safe mode"),
                        BarColumn(bar_width=None, style=FAINT, complete_style=PINK, finished_style=ORANGE),
                        MofNCompleteColumn(), console=console, transient=True)
    with progress:
        task = progress.add_task("", total=count)
        while len(messages) < count and failures < 3:
            params = {"limit": min(batch, count - len(messages))}
            if cursor:
                params["cursor"] = cursor
            try:
                result = client.private_request(f"direct_v2/threads/{thread_id}/", params=params)
                items = (result or {}).get("thread", {}).get("items", [])
                if not items:
                    break
                parsed = []
                for item in items:
                    try:
                        cleaned = clean_item(item)
                        if cleaned:
                            parsed.append(extract_direct_message(cleaned))
                    except Exception:
                        pass
                cursor = items[-1].get("item_id")
                if parsed:
                    messages.extend(parsed)
                    progress.update(task, completed=len(messages))
                    failures = 0
                else:
                    failures += 1
            except Exception:
                failures += 1
                batch = max(5, batch // 2)
    return messages


def name_map(client, thread):
    names = {u.pk: u.username for u in thread.users}
    names[client.user_id] = client.username or "you"
    for k, v in list(names.items()):  # pk can be str or int depending on version
        names[str(k)] = v
    return names


def sender_of(msg, names):
    return names.get(msg.user_id) or names.get(str(msg.user_id)) or f"unknown ({msg.user_id})"


def show_chat(client, thread, messages, last=12):
    """Show the newest messages as chat bubbles."""
    from rich import box
    from rich.align import Align
    from rich.cells import cell_len
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.text import Text

    names = name_map(client, thread)
    ordered = sorted(messages, key=lambda m: m.timestamp)
    shown = ordered[-last:]
    max_w = max(24, int(console.width * 0.62))

    console.print()
    console.print(Rule(Text.assemble((f" @{thread_name(thread)} ", f"bold {PINK}"),
                                     (f"· {len(ordered):,} messages, showing the last {len(shown)} ", MUTED)),
                       style=FAINT))
    day = None
    for m in shown:
        if m.timestamp.date() != day:
            day = m.timestamp.date()
            console.print()
            console.print(Align.center(Text(f"{day:%A %d %B %Y}", style=f"italic {FAINT}")))
        mine = str(m.user_id) == str(client.user_id)
        kind, _ = media_info(m)
        body = m.text if m.text else ("▣ " + kind.lower() if kind else "▣ media / shared post")
        width = min(max_w, max(cell_len(line) for line in body.splitlines() or [""]) + 6, )
        width = max(width, cell_len(sender_of(m, names)) + 10, 22)
        bubble = Panel(
            Text(body, style="white"),
            box=box.ROUNDED, padding=(0, 1), width=min(width, max_w),
            border_style=PINK if mine else FAINT,
            title=None if mine else f"[bold {ORANGE}]{sender_of(m, names)}[/]", title_align="left",
            subtitle=f"[{FAINT}]{m.timestamp:%H:%M}[/]", subtitle_align="right",
        )
        console.print(Align.right(bubble) if mine else Align.left(bubble))
    console.print(Rule(style=FAINT))
    console.print()


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

def export(client, thread, messages, fmt, folder):
    names = name_map(client, thread)
    ordered = sorted(messages, key=lambda m: m.timestamp)
    who = safe_filename(thread.users[0].username if thread.users else "unknown")
    out_dir = folder / who
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{who}_{datetime.now():%Y-%m-%d_%H-%M-%S}.{fmt}"

    if fmt == "txt":
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Conversation with {thread_name(thread)}\n{'=' * 70}\n")
            current_day = None
            for m in ordered:
                if m.timestamp.date() != current_day:
                    current_day = m.timestamp.date()
                    f.write(f"\n{'-' * 20} {current_day:%A, %B %d, %Y} {'-' * 20}\n\n")
                text = m.text if m.text is not None else "[no text]"
                f.write(f"{m.timestamp:%H:%M:%S} - {sender_of(m, names)}: {text}\n")
                kind, url = media_info(m)
                if kind:
                    f.write(f"  [{kind}: {url}]\n")

    elif fmt == "json":
        data = {
            "conversation_info": {
                "participants": [u.username for u in thread.users],
                "thread_id": thread.id,
                "export_time": datetime.now().isoformat(),
                "message_count": len(ordered),
            },
            "messages": [],
        }
        for m in ordered:
            entry = {
                "timestamp": m.timestamp.isoformat(),
                "sender": sender_of(m, names),
                "sender_id": m.user_id,
                "text": m.text,
                "message_id": getattr(m, "id", None),
            }
            kind, url = media_info(m)
            if kind:
                entry["media"] = {"type": kind.lower(), "url": url}
            data["messages"].append(entry)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    else:  # csv
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Timestamp", "Date", "Time", "Sender", "Sender_ID", "Message", "Media_Type", "Media_URL"])
            for m in ordered:
                kind, url = media_info(m)
                w.writerow([m.timestamp.isoformat(), f"{m.timestamp:%Y-%m-%d}", f"{m.timestamp:%H:%M:%S}",
                            sender_of(m, names), m.user_id, m.text or "", kind or "", url or ""])
    return path


def pick_format():
    from rich.table import Table
    grid = Table.grid(padding=(0, 2))
    grid.add_column()
    grid.add_column(style="bold white")
    grid.add_column(style=MUTED)
    grid.add_row(pill(1, PURPLE), "TXT", "easy to read, like a chat log")
    grid.add_row(pill(2, PINK), "JSON", "structured, for programs")
    grid.add_row(pill(3, ORANGE), "CSV", "opens in Excel / Sheets")
    console.print()
    centered(panel(grid, title="save as", width=min(60, console.width - 4), padding=(1, 3)))
    console.print()
    return {"1": "txt", "2": "json", "3": "csv"}[ask_choice("format", ["1", "2", "3"], "1")]


def saved_box(path, count):
    from rich.text import Text
    body = Text.assemble(("✓ ", f"bold {GOOD}"), (f"saved {count:,} messages\n\n", "bold white"),
                         (str(path.parent) + os.sep, MUTED), (path.name, f"bold {PINK}"))
    console.print()
    centered(panel(body, title="done", color=GOOD, width=min(90, console.width - 4)))
    console.print()


# --------------------------------------------------------------------------
# Menu flows
# --------------------------------------------------------------------------

def fetch_flow(state):
    if state.get("client") is None:
        console.print()
        state["client"] = login(state)
    client = state["client"]

    threads = get_conversations(client)
    if not threads:
        state["notice"] = ("info", "your inbox is empty")
        return

    while True:
        header(state)
        show_inbox(threads)
        thread = pick_conversation(threads)
        count_str = ask("how many messages", f"{DEFAULT_COUNT}").replace(",", "").replace(".", "")
        count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else DEFAULT_COUNT

        messages = fetch_messages(client, thread, count)
        if not messages:
            say("no messages could be retrieved from this chat", "err")
        else:
            show_chat(client, thread, messages)
            if ask_yes("save these messages to a file?", True):
                fmt = pick_format()
                with spinner("writing file"):
                    path = export(client, thread, messages, fmt, save_dir(state["settings"]))
                saved_box(path, len(messages))

        if not ask_yes("open another chat?", False):
            return


def change_save_dir(state):
    settings = state["settings"]
    console.print()
    say(f"current folder: [{PINK}]{save_dir(settings)}[/]", "dim")
    new = ask("new folder (leave empty to keep it)", "")
    if not new:
        return
    path = Path(new.strip('"')).expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
        settings["save_dir"] = str(path)
        save_settings(settings)
        state["notice"] = ("ok", "save folder updated")
    except Exception as e:
        state["notice"] = ("err", f"couldn't use that folder: {e}")


def logout(state):
    state["client"] = None
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
    state["settings"].pop("username", None)
    save_settings(state["settings"])
    state["notice"] = ("ok", "logged out, your saved session is deleted")


def main_menu(state):
    from rich.table import Table

    logged_in = state.get("client") is not None or SESSION_FILE.exists()
    grid = Table.grid(padding=(0, 2))
    grid.add_column()
    grid.add_column(style="bold white")
    grid.add_column(style=MUTED)
    grid.add_row(pill(1, PURPLE), "Fetch messages", "pick a chat and save it")
    grid.add_row(pill(2, PINK), "Save folder", "change where files go")
    grid.add_row(pill(3, ORANGE), "Log out" if logged_in else "Forget login", "delete the saved session")
    grid.add_row(pill(4, FAINT), "Exit", "")
    centered(panel(grid, title="menu", width=min(60, console.width - 4), padding=(1, 3)))
    console.print()
    return ask_choice("choose", ["1", "2", "3", "4"], "1")


def goodbye():
    from rich.align import Align
    console.print()
    console.print(Align.center(gradient("✦  see you next time  ✦")))
    console.print()


def main():
    ensure_requirements()
    init_ui()

    state = {"client": None, "settings": load_settings()}
    while True:
        header(state)
        choice = main_menu(state)
        try:
            if choice == "1":
                fetch_flow(state)
            elif choice == "2":
                change_save_dir(state)
            elif choice == "3":
                logout(state)
            else:
                goodbye()
                return
        except LoginCancelled:
            state["notice"] = ("info", "login cancelled")
        except KeyboardInterrupt:
            state["notice"] = ("info", "cancelled")
        except Exception as e:
            error_box("something went wrong", e)
            console.input(f"  [{FAINT}]press Enter to go back to the menu[/] ")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError, SystemExit):
        pass
    except Exception as e:
        print(f"\n  Unexpected error: {e}")
    finally:
        # Keep the window open when started by double-click.
        try:
            input("\n  Press Enter to close...")
        except Exception:
            pass
