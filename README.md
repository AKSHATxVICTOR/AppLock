# 🔐 Windows App Locker

A Python-based application locker for Windows that prevents selected `.exe` files
from running unless unlocked via a password-protected CLI command.

---

## 📁 Project Structure

```
app-locker/
├── main_gui.py      — Tkinter control panel (lock/unlock apps, manage watcher)
├── watcher.py       — Background process monitor (kills locked apps on detection)
├── unlock_cli.py    — Terminal unlock tool (verify password → launch app)
├── utils.py         — Shared: hashing, config read/write, logging
├── config.json      — Stores locked app entries (auto-created, do not edit manually)
└── app_locker.log   — Activity log (auto-created)
```

---

## ⚙️ Requirements

```bash
pip install psutil
```

> Python 3.10+ is required (uses `int | None` type hints).  
> Tkinter is included with standard Python on Windows.

---

## 🚀 Quick Start

### 1. Open the Control Panel (GUI)

```bash
python main_gui.py
```

- Click **Browse** → select a `.exe` file
- Enter a password (min 4 characters)
- Click **🔒 Lock This App**
- The **Watcher** starts automatically in the background

### 2. Unlock and Launch an App

```bash
python unlock_cli.py
```

Or directly:

```bash
python unlock_cli.py --app whatsapp.exe
```

- Enter the correct password → app launches
- 3 wrong attempts → 30-second lockout

### 3. List Locked Apps

```bash
python unlock_cli.py --list
```

### 4. Run the Watcher Manually

```bash
python watcher.py
```

---

## 🔐 Security Details

| Feature              | Implementation                          |
|----------------------|-----------------------------------------|
| Password storage     | SHA-256 hash (never stored in plain)    |
| App name keys        | Normalised to lowercase                 |
| Config corruption    | Graceful fallback to empty config       |
| Password input       | `getpass` (hidden in terminal)          |
| Retry limit          | 3 attempts before 30s lockout           |
| Whitelist            | PID whitelist prevents self-kill        |
| Logging              | `app_locker.log` + console              |

---

## ⚠️ Important Notes

- **Run as Administrator** on Windows for reliable process termination.
  Some system-protected apps may resist `psutil.terminate()`.
- The watcher polls every 1.5 seconds — there is a small window between
  when an app opens and when it gets killed. This is normal.
- The GUI auto-starts the watcher; closing the GUI gives you the option
  to stop it too.

---

## 🔄 Functional Flow

```
User (GUI)  →  Locks app  →  config.json  ←  watcher.py reads
                                                    ↓
Direct open →  watcher detects PID  →  kills process

User (CLI)  →  unlock_cli.py  →  verify password  →  launch app
                                                    ↓
                                         PID → .unlocked_pids whitelist
                                                    ↓
                                         watcher skips this PID ✓
```
