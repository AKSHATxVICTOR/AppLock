"""
utils.py - Shared utilities for App Locker System
Handles: SHA256 hashing, config read/write, logging
"""

import hashlib
import json
import os
import logging
from datetime import datetime

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "app_locker.log")

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AppLocker")


# ─── Hashing ──────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a password using SHA256. Returns hex digest string."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Compare a plain password against a stored SHA256 hash."""
    return hash_password(plain) == hashed


# ─── Config Handling ──────────────────────────────────────────────────────────
def load_config() -> dict:
    """
    Load the locked-apps config from disk.
    Returns an empty dict if file is missing or corrupt.

    Config format:
    {
        "whatsapp.exe": {
            "path": "C:\\...\\WhatsApp.exe",
            "password_hash": "<sha256>",
            "locked": true
        },
        ...
    }
    """
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure all keys are normalised to lowercase
        return {k.lower(): v for k, v in data.items()}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Config read error ({e}). Starting with empty config.")
        return {}


def save_config(config: dict) -> bool:
    """Persist the config dict to disk. Returns True on success."""
    try:
        # Normalise keys before saving
        normalised = {k.lower(): v for k, v in config.items()}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(normalised, f, indent=4)
        return True
    except OSError as e:
        logger.error(f"Failed to save config: {e}")
        return False


def add_locked_app(exe_name: str, exe_path: str, password: str) -> bool:
    """
    Add or update a locked app entry.
    exe_name  – e.g. "WhatsApp.exe"  (will be stored lowercase)
    exe_path  – full path to the executable
    password  – plain text (will be hashed before storage)
    """
    config = load_config()
    key = exe_name.lower()
    config[key] = {
        "path": exe_path,
        "password_hash": hash_password(password),
        "locked": True,
        "added_at": datetime.now().isoformat()
    }
    return save_config(config)


def remove_locked_app(exe_name: str) -> bool:
    """Remove an app from the locked list."""
    config = load_config()
    key = exe_name.lower()
    if key in config:
        del config[key]
        return save_config(config)
    return False


def get_locked_apps() -> dict:
    """Return only apps that are currently locked."""
    return {k: v for k, v in load_config().items() if v.get("locked", True)}


def normalise_name(exe_name: str) -> str:
    """Return lowercase exe name, adding .exe if missing."""
    name = exe_name.strip().lower()
    if not name.endswith(".exe"):
        name += ".exe"
    return name
