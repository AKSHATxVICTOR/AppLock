"""
main_gui.py - App Locker Control Panel (Tkinter GUI)
Provides a clean interface to:
  • Add / remove locked apps
  • View currently locked apps
  • Start / stop the background watcher
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import (
    add_locked_app, remove_locked_app, load_config,
    normalise_name, logger
)

# ─── Colour Palette ───────────────────────────────────────────────────────────
BG          = "#0f0f13"
PANEL       = "#1a1a24"
ACCENT      = "#7c5cfc"
ACCENT_DARK = "#5a3dd4"
DANGER      = "#e05260"
SUCCESS     = "#3ddc97"
TEXT        = "#e8e8f0"
SUBTEXT     = "#888899"
BORDER      = "#2a2a38"
ENTRY_BG    = "#12121a"
FONT_MAIN   = ("Segoe UI", 10)
FONT_TITLE  = ("Segoe UI Semibold", 13)
FONT_MONO   = ("Consolas", 9)


class AppLockerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("App Locker – Control Panel")
        self.root.geometry("780x640")
        self.root.minsize(700, 560)
        self.root.configure(bg=BG)

        # Watcher process handle
        self._watcher_proc: subprocess.Popen | None = None
        self._watcher_thread: threading.Thread | None = None

        self._build_ui()
        self._refresh_table()

        # Auto-start watcher on launch
        self._start_watcher()

        # Clean shutdown
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══════════════════════════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # ── Header bar ────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=PANEL, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="🔐  App Locker",
            bg=PANEL, fg=TEXT, font=("Segoe UI Semibold", 15),
            padx=20
        ).pack(side="left", pady=10)

        # Watcher status indicator
        self._status_var = tk.StringVar(value="● Watcher: starting…")
        self._status_lbl = tk.Label(
            header, textvariable=self._status_var,
            bg=PANEL, fg=SUBTEXT, font=FONT_MAIN, padx=20
        )
        self._status_lbl.pack(side="right", pady=10)

        # ── Main split layout ─────────────────────────────────────────────
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=14)

        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self._build_form(body)
        self._build_table(body)

        # ── Status bar ───────────────────────────────────────────────────
        statusbar = tk.Frame(self.root, bg=BORDER, height=28)
        statusbar.pack(fill="x", side="bottom")
        statusbar.pack_propagate(False)

        self._info_var = tk.StringVar(value="Ready.")
        tk.Label(
            statusbar, textvariable=self._info_var,
            bg=BORDER, fg=SUBTEXT, font=FONT_MONO, padx=12
        ).pack(side="left", pady=4)

    # ─── Left panel: Add app form ─────────────────────────────────────────────
    def _build_form(self, parent):
        frame = tk.Frame(parent, bg=PANEL, bd=0, highlightthickness=1,
                         highlightbackground=BORDER)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(frame, text="Lock New App",
                 bg=PANEL, fg=TEXT, font=FONT_TITLE,
                 pady=14, padx=16).pack(anchor="w")

        sep = tk.Frame(frame, bg=BORDER, height=1)
        sep.pack(fill="x")

        inner = tk.Frame(frame, bg=PANEL, padx=16, pady=14)
        inner.pack(fill="both", expand=True)

        # ── App path ──────────────────────────────────────────────────────
        self._lbl(inner, "Executable Path")
        path_row = tk.Frame(inner, bg=PANEL)
        path_row.pack(fill="x", pady=(0, 10))

        self._path_var = tk.StringVar()
        path_entry = tk.Entry(
            path_row, textvariable=self._path_var,
            bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=6, font=FONT_MONO
        )
        path_entry.pack(side="left", fill="x", expand=True)

        self._btn(path_row, "Browse", self._browse_file,
                  color=ACCENT).pack(side="right", padx=(6, 0))

        # ── App display name ──────────────────────────────────────────────
        self._lbl(inner, "App Name  (auto-filled)")
        self._name_var = tk.StringVar()
        tk.Entry(
            inner, textvariable=self._name_var,
            bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=6, font=FONT_MONO
        ).pack(fill="x", pady=(0, 10))

        # Sync name from path
        self._path_var.trace_add("write", self._sync_name)

        # ── Password ──────────────────────────────────────────────────────
        self._lbl(inner, "Password")
        self._pw_var = tk.StringVar()
        tk.Entry(
            inner, textvariable=self._pw_var,
            show="●",
            bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=6, font=FONT_MAIN
        ).pack(fill="x", pady=(0, 4))

        # ── Confirm password ──────────────────────────────────────────────
        self._lbl(inner, "Confirm Password")
        self._pw2_var = tk.StringVar()
        tk.Entry(
            inner, textvariable=self._pw2_var,
            show="●",
            bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=6, font=FONT_MAIN
        ).pack(fill="x", pady=(0, 16))

        # ── Lock button ───────────────────────────────────────────────────
        self._btn(inner, "🔒  Lock This App", self._lock_app,
                  color=ACCENT, fullwidth=True).pack(fill="x", pady=(0, 8))

        # ── Watcher controls ──────────────────────────────────────────────
        sep2 = tk.Frame(inner, bg=BORDER, height=1)
        sep2.pack(fill="x", pady=(10, 12))

        tk.Label(inner, text="Watcher Service",
                 bg=PANEL, fg=SUBTEXT, font=("Segoe UI", 9)).pack(anchor="w")

        ctrl_row = tk.Frame(inner, bg=PANEL)
        ctrl_row.pack(fill="x", pady=(6, 0))

        self._btn(ctrl_row, "▶ Start", self._start_watcher,
                  color=SUCCESS).pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._btn(ctrl_row, "■ Stop", self._stop_watcher,
                  color=DANGER).pack(side="left", expand=True, fill="x")

    # ─── Right panel: Locked apps table ──────────────────────────────────────
    def _build_table(self, parent):
        frame = tk.Frame(parent, bg=PANEL, bd=0, highlightthickness=1,
                         highlightbackground=BORDER)
        frame.grid(row=0, column=1, sticky="nsew")

        header_row = tk.Frame(frame, bg=PANEL)
        header_row.pack(fill="x", padx=16, pady=12)

        tk.Label(header_row, text="Locked Applications",
                 bg=PANEL, fg=TEXT, font=FONT_TITLE).pack(side="left")

        self._btn(header_row, "🗑 Remove Selected", self._remove_app,
                  color=DANGER).pack(side="right")
        self._btn(header_row, "↻ Refresh", self._refresh_table,
                  color=ACCENT).pack(side="right", padx=(0, 8))

        sep = tk.Frame(frame, bg=BORDER, height=1)
        sep.pack(fill="x")

        # Table
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Locker.Treeview",
                         background=ENTRY_BG,
                         foreground=TEXT,
                         fieldbackground=ENTRY_BG,
                         borderwidth=0,
                         rowheight=28,
                         font=FONT_MONO)
        style.configure("Locker.Treeview.Heading",
                         background=BORDER,
                         foreground=SUBTEXT,
                         borderwidth=0,
                         font=("Segoe UI Semibold", 9))
        style.map("Locker.Treeview",
                  background=[("selected", ACCENT_DARK)],
                  foreground=[("selected", TEXT)])

        cols = ("name", "path", "added")
        self._tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            style="Locker.Treeview", selectmode="browse"
        )
        self._tree.heading("name", text="App Name")
        self._tree.heading("path", text="Path")
        self._tree.heading("added", text="Added")
        self._tree.column("name", width=130, minwidth=100)
        self._tree.column("path", width=280, minwidth=160)
        self._tree.column("added", width=140, minwidth=110)

        scrollbar = ttk.Scrollbar(frame, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.pack(side="right", fill="y", pady=8, padx=(0, 4))

    # ══════════════════════════════════════════════════════════════════════════
    #  WIDGET HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _lbl(self, parent, text: str):
        tk.Label(parent, text=text,
                 bg=PANEL, fg=SUBTEXT, font=("Segoe UI", 9)
                 ).pack(anchor="w", pady=(4, 2))

    def _btn(self, parent, text: str, cmd, color=ACCENT, fullwidth=False):
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=color, fg="white", activebackground=color,
            activeforeground="white",
            relief="flat", bd=0, padx=12, pady=6,
            font=("Segoe UI Semibold", 9), cursor="hand2"
        )
        return b

    # ══════════════════════════════════════════════════════════════════════════
    #  CALLBACKS
    # ══════════════════════════════════════════════════════════════════════════

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Executable",
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self._path_var.set(path)

    def _sync_name(self, *_):
        """Auto-populate the name field from the selected path."""
        path = self._path_var.get()
        if path:
            self._name_var.set(os.path.basename(path))

    def _lock_app(self):
        path = self._path_var.get().strip()
        name = self._name_var.get().strip()
        pw   = self._pw_var.get()
        pw2  = self._pw2_var.get()

        # ── Validation ────────────────────────────────────────────────────
        if not path:
            messagebox.showerror("Error", "Please select an executable path.")
            return
        if not os.path.isfile(path):
            messagebox.showerror("Error", f"File not found:\n{path}")
            return
        if not name:
            messagebox.showerror("Error", "App name cannot be empty.")
            return
        if not pw:
            messagebox.showerror("Error", "Password cannot be empty.")
            return
        if pw != pw2:
            messagebox.showerror("Error", "Passwords do not match.")
            return
        if len(pw) < 4:
            messagebox.showerror("Error", "Password must be at least 4 characters.")
            return

        # ── Save ──────────────────────────────────────────────────────────
        if add_locked_app(name, path, pw):
            logger.info(f"GUI locked app: {name} -> {path}")
            self._info(f"✓  '{normalise_name(name)}' is now locked.")
            self._refresh_table()
            # Clear form
            self._path_var.set("")
            self._name_var.set("")
            self._pw_var.set("")
            self._pw2_var.set("")
        else:
            messagebox.showerror("Error", "Failed to save config. Check logs.")

    def _remove_app(self):
        selected = self._tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select an app from the list first.")
            return

        item    = self._tree.item(selected[0])
        appname = item["values"][0]

        if not messagebox.askyesno(
            "Confirm Remove",
            f"Remove lock on '{appname}'?\n\nThe app will be freely accessible again."
        ):
            return

        if remove_locked_app(appname):
            logger.info(f"GUI removed lock: {appname}")
            self._info(f"✓  '{appname}' has been unlocked and removed.")
            self._refresh_table()
        else:
            messagebox.showerror("Error", f"Could not remove '{appname}'.")

    def _refresh_table(self):
        for row in self._tree.get_children():
            self._tree.delete(row)

        config = load_config()
        for name, data in config.items():
            if data.get("locked", True):
                added = data.get("added_at", "")[:10]
                path  = data.get("path", "")
                self._tree.insert("", "end", values=(name, path, added))

        count = len(self._tree.get_children())
        self._info(f"{count} app(s) currently locked.")

    # ── Watcher controls ──────────────────────────────────────────────────────
    def _start_watcher(self):
        if self._watcher_proc and self._watcher_proc.poll() is None:
            self._info("Watcher is already running.")
            return

        watcher_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "watcher.py")
        try:
            self._watcher_proc = subprocess.Popen(
                [sys.executable, watcher_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self._set_watcher_status(True)
            logger.info(f"Watcher started (PID {self._watcher_proc.pid})")
            self._info(f"Watcher started (PID {self._watcher_proc.pid})")
        except Exception as e:
            messagebox.showerror("Error", f"Could not start watcher:\n{e}")

    def _stop_watcher(self):
        if self._watcher_proc and self._watcher_proc.poll() is None:
            self._watcher_proc.terminate()
            self._watcher_proc = None
            self._set_watcher_status(False)
            logger.info("Watcher stopped by user")
            self._info("Watcher stopped.")
        else:
            self._info("Watcher is not running.")

    def _set_watcher_status(self, running: bool):
        if running:
            self._status_var.set("● Watcher: active")
            self._status_lbl.configure(fg=SUCCESS)
        else:
            self._status_var.set("● Watcher: stopped")
            self._status_lbl.configure(fg=DANGER)

    # ── Status bar ────────────────────────────────────────────────────────────
    def _info(self, msg: str):
        self._info_var.set(msg)

    # ── Shutdown ──────────────────────────────────────────────────────────────
    def _on_close(self):
        if self._watcher_proc and self._watcher_proc.poll() is None:
            if messagebox.askyesno(
                "Exit",
                "The watcher is still running.\n\nStop the watcher and exit?"
            ):
                self._stop_watcher()
                self.root.destroy()
        else:
            self.root.destroy()


# ─── Entry Point ──────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    app  = AppLockerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
