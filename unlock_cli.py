"""
unlock_cli.py - Terminal-based App Unlock Tool
Usage:
    python unlock_cli.py
    python unlock_cli.py --app whatsapp.exe

The script:
  1. Asks for the app name (or takes it via --app flag)
  2. Securely prompts for the password (hidden input)
  3. Verifies against the stored hash
  4. On success: launches the app and whitelists its PID
  5. On failure: enforces a retry limit then locks the terminal
"""

import argparse
import getpass
import subprocess
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import (
    load_config, verify_password, normalise_name, logger
)
from watcher import add_whitelisted_pid

# ─── Constants ────────────────────────────────────────────────────────────────
MAX_ATTEMPTS    = 3          # Wrong password attempts before lockout
LOCKOUT_SECONDS = 30         # Cooldown after too many bad attempts
BANNER = r"""
╔═══════════════════════════════════════════╗
║          🔐  App Locker – Unlock          ║
╚═══════════════════════════════════════════╝
"""


# ─── Helpers ──────────────────────────────────────────────────────────────────
def list_locked_apps(config: dict):
    """Print all currently locked apps."""
    locked = {k: v for k, v in config.items() if v.get("locked", True)}
    if not locked:
        print("  (no apps are currently locked)")
        return
    print("\n  Locked apps:")
    for name, data in locked.items():
        path = data.get("path", "unknown path")
        print(f"    • {name}  →  {path}")
    print()


def launch_app(exe_path: str) -> int | None:
    """
    Launch the given executable as a detached process.
    Returns the PID on success, None on failure.
    """
    try:
        if sys.platform == "win32":
            # Windows: DETACHED_PROCESS prevents the new window from being
            # tied to this console session
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            proc = subprocess.Popen(
                [exe_path],
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
        else:
            # Linux / macOS (for development / testing)
            proc = subprocess.Popen(
                [exe_path],
                start_new_session=True,
                close_fds=True
            )
        return proc.pid
    except FileNotFoundError:
        print(f"\n  ✗  Executable not found: {exe_path}")
        logger.error(f"Launch failed – file not found: {exe_path}")
        return None
    except PermissionError:
        print(f"\n  ✗  Permission denied: {exe_path}")
        logger.error(f"Launch failed – permission denied: {exe_path}")
        return None
    except Exception as e:
        print(f"\n  ✗  Could not launch app: {e}")
        logger.error(f"Launch failed: {e}")
        return None


# ─── Main Unlock Flow ─────────────────────────────────────────────────────────
def unlock_flow(app_name: str | None = None):
    print(BANNER)

    config = load_config()

    if not config:
        print("  No apps are locked yet. Use the GUI to lock apps first.\n")
        return

    # ── App selection ──────────────────────────────────────────────────────
    if app_name:
        target = normalise_name(app_name)
    else:
        list_locked_apps(config)
        raw = input("  Enter app name (e.g. whatsapp.exe): ").strip()
        if not raw:
            print("  No app name entered. Exiting.")
            return
        target = normalise_name(raw)

    if target not in config:
        print(f"\n  ✗  '{target}' is not in the locked apps list.")
        logger.info(f"Unlock attempt for unknown app: {target}")
        return

    entry = config[target]
    if not entry.get("locked", True):
        print(f"\n  ℹ  '{target}' is not currently locked.")
        return

    exe_path = entry.get("path")
    if not exe_path:
        print(f"\n  ✗  No path found for '{target}'. Please re-add it via the GUI.")
        return

    # ── Password verification with retry limit ─────────────────────────────
    print(f"\n  App : {target}")
    print(f"  Path: {exe_path}\n")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            password = getpass.getpass(
                prompt=f"  Password (attempt {attempt}/{MAX_ATTEMPTS}): "
            )
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Unlock cancelled.")
            return

        if verify_password(password, entry["password_hash"]):
            print(f"\n  ✓  Password correct! Launching {target}...\n")
            logger.info(f"Unlock SUCCESS: '{target}'")

            pid = launch_app(exe_path)
            if pid:
                add_whitelisted_pid(pid)
                print(f"  ✓  Launched '{target}' (PID {pid})\n")
                logger.info(f"Launched '{target}' with PID {pid}")
            return

        else:
            remaining = MAX_ATTEMPTS - attempt
            if remaining > 0:
                print(f"\n  ✗  Wrong password. {remaining} attempt(s) remaining.\n")
                logger.warning(f"Failed unlock attempt {attempt} for '{target}'")
            else:
                print(f"\n  ✗  Wrong password.")

    # ── Lockout ────────────────────────────────────────────────────────────
    logger.warning(f"LOCKOUT: Max attempts reached for '{target}'")
    print(f"\n  ⛔  Too many failed attempts.")
    print(f"  Access denied. Please wait {LOCKOUT_SECONDS} seconds.\n")

    for remaining in range(LOCKOUT_SECONDS, 0, -1):
        print(f"  Locked for {remaining:2d} seconds...", end="\r")
        time.sleep(1)
    print("\n  Lockout expired. Run the script again to retry.\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="App Locker – Unlock a locked application"
    )
    parser.add_argument(
        "--app", "-a",
        metavar="APP_NAME",
        help="Name of the app to unlock (e.g. whatsapp.exe)",
        default=None
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all currently locked apps and exit"
    )
    args = parser.parse_args()

    if args.list:
        print(BANNER)
        list_locked_apps(load_config())
    else:
        unlock_flow(app_name=args.app)
