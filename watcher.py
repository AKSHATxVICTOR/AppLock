"""
watcher.py - Background Process Watcher
Continuously monitors running processes and kills any locked app
that was opened directly (without going through unlock_cli.py).

Run as a separate process:  python watcher.py
"""

import psutil
import time
import sys
import os
import signal
import logging

# Allow imports from parent dir when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import get_locked_apps, logger

# ─── Config ───────────────────────────────────────────────────────────────────
POLL_INTERVAL   = 1.5   # seconds between scans
KILL_RETRIES    = 3     # attempts to terminate a process before giving up
KILL_WAIT       = 0.5   # seconds to wait after each kill attempt

# ─── Whitelist: PIDs that were launched by unlock_cli.py ──────────────────────
# unlock_cli writes the PID of the child process here so the watcher knows
# not to kill it.  Uses a small temp file for cross-process communication.
WHITELIST_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".unlocked_pids")


def load_whitelisted_pids() -> set:
    """Return the set of PIDs that were legitimately launched via CLI unlock."""
    if not os.path.exists(WHITELIST_FILE):
        return set()
    try:
        with open(WHITELIST_FILE) as f:
            return {int(line.strip()) for line in f if line.strip().isdigit()}
    except (OSError, ValueError):
        return set()


def add_whitelisted_pid(pid: int):
    """Called by unlock_cli after a successful launch."""
    try:
        with open(WHITELIST_FILE, "a") as f:
            f.write(f"{pid}\n")
    except OSError as e:
        logger.warning(f"Could not write whitelist PID {pid}: {e}")


def clean_whitelist(whitelisted: set) -> set:
    """
    Remove PIDs from the whitelist whose processes have already exited.
    Keeps the file from growing indefinitely.
    """
    active = {pid for pid in whitelisted if psutil.pid_exists(pid)}
    if active != whitelisted:
        try:
            with open(WHITELIST_FILE, "w") as f:
                for pid in active:
                    f.write(f"{pid}\n")
        except OSError:
            pass
    return active


def kill_process(proc: psutil.Process) -> bool:
    """
    Attempt to terminate then force-kill a process.
    Returns True if the process is gone after attempts.
    """
    for attempt in range(KILL_RETRIES):
        try:
            if not proc.is_running():
                return True
            if attempt == 0:
                proc.terminate()          # SIGTERM / polite kill
            else:
                proc.kill()               # SIGKILL / forceful
            time.sleep(KILL_WAIT)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return True   # Already gone or can't touch it

    return not proc.is_running()


def scan_and_enforce():
    """
    One pass: iterate all running processes and kill any that match a locked app
    unless their PID is in the whitelist.
    """
    locked = get_locked_apps()          # fresh read each pass
    if not locked:
        return

    whitelisted = load_whitelisted_pids()
    whitelisted = clean_whitelist(whitelisted)

    try:
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                proc_name = (proc.info["name"] or "").lower()
                proc_pid  = proc.info["pid"]

                if proc_name in locked:
                    if proc_pid in whitelisted:
                        continue   # This was launched by us — leave it alone

                    # ── BLOCKED ──────────────────────────────────────────────
                    app_path = locked[proc_name].get("path", proc_name)
                    logger.warning(
                        f"BLOCKED: '{proc_name}' (PID {proc_pid}) "
                        f"opened without unlock. Killing..."
                    )

                    success = kill_process(proc)
                    if success:
                        logger.info(f"Successfully terminated '{proc_name}' (PID {proc_pid})")
                    else:
                        logger.error(
                            f"Failed to terminate '{proc_name}' (PID {proc_pid}). "
                            f"May require elevated privileges."
                        )

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process vanished or we lack permissions — not our concern
                continue

    except Exception as e:
        logger.error(f"Unexpected error during scan: {e}")


# ─── Entry Point ──────────────────────────────────────────────────────────────
def run_watcher():
    """Main watcher loop. Runs until interrupted (Ctrl+C or SIGTERM)."""
    logger.info("=" * 55)
    logger.info("  App Locker Watcher started")
    logger.info(f"  Poll interval : {POLL_INTERVAL}s")
    logger.info(f"  Config file   : utils.CONFIG_FILE")
    logger.info("  Press Ctrl+C to stop")
    logger.info("=" * 55)

    def handle_exit(signum, frame):
        logger.info("Watcher received stop signal. Shutting down.")
        sys.exit(0)

    signal.signal(signal.SIGINT,  handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    while True:
        scan_and_enforce()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_watcher()
