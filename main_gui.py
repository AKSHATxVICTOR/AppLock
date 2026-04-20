"""
Requires:  pip install PyQt6
"""

import sys
import os
import subprocess
import ctypes

# ── DPI awareness before Qt initialises ───────────────────────────────────────
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QMessageBox, QAbstractItemView,
    QSpacerItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import add_locked_app, remove_locked_app, load_config, normalise_name, logger

# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════
C = {
    "bg":           "#0b0b0f",
    "surface":      "#13131a",
    "surface2":     "#1c1c28",
    "border":       "#252535",
    "border_focus": "#3E436F",
    "accent":       "#3E436F",
    "accent_hover": "#3E436F",
    "accent_press": "#3E436F",
    "danger":       "#e05260",
    "danger_hover": "#ea6370",
    "success":      "#3ddc97",
    "success_hover":"#4ef0a8",
    "text":         "#eeeef5",
    "subtext":      "#7777aa",
    "muted":        "#44445a",
    "input_bg":     "#0f0f18",
    "row_alt":      "#161622",
    "row_hover":    "#1e1e30",
    "row_sel":      "#2a2050",
    "header_bg":    "#181825",
}

STYLESHEET = f"""
QMainWindow, QWidget#root {{
    background: {C['bg']};
}}
QLabel {{
    color: {C['text']};
    background: transparent;
}}
QLineEdit {{
    background: {C['input_bg']};
    color: {C['text']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-family: "Consolas", monospace;
    font-size: 11px;
    selection-background-color: {C['accent']};
}}
QLineEdit:focus {{
    border-color: {C['border_focus']};
    background: #12121f;
}}
QLineEdit:hover {{
    border-color: {C['muted']};
}}
QScrollBar:vertical {{
    background: {C['surface']};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C['muted']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QTableWidget {{
    background: {C['surface']};
    color: {C['text']};
    border: none;
    gridline-color: {C['border']};
    font-size: 11px;
    font-family: "Consolas", monospace;
    selection-background-color: {C['row_sel']};
    outline: none;
    alternate-background-color: {C['row_alt']};
}}
QTableWidget::item {{
    padding: 6px 12px;
    border: none;
}}
QTableWidget::item:selected {{
    background: {C['row_sel']};
    color: {C['text']};
}}
QTableWidget::item:hover {{
    background: {C['row_hover']};
}}
QHeaderView::section {{
    background: {C['header_bg']};
    color: {C['subtext']};
    font-family: "Segoe UI Semibold", sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {C['border']};
}}
QToolTip {{
    background: {C['surface2']};
    color: {C['text']};
    border: 1px solid {C['border']};
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 10px;
}}
QMessageBox {{
    background: {C['surface']};
}}
QMessageBox QLabel {{
    color: {C['text']};
    font-size: 12px;
}}
QMessageBox QPushButton {{
    background: {C['accent']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 20px;
    font-size: 11px;
    min-width: 70px;
}}
QMessageBox QPushButton:hover {{
    background: {C['accent_hover']};
}}
"""


# ══════════════════════════════════════════════════════════════════════════════
#  REUSABLE WIDGETS
# ══════════════════════════════════════════════════════════════════════════════

class GlowButton(QPushButton):
    def __init__(self, text, color=None, hover_color=None, parent=None):
        super().__init__(text, parent)
        color       = color or C["accent"]
        hover_color = hover_color or color
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 9px;
                padding: 9px 18px;
                font-family: "Segoe UI Semibold", sans-serif;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {hover_color};
            }}
            QPushButton:pressed {{
                background: {color};
                padding-top: 11px;
                padding-bottom: 7px;
            }}
            QPushButton:disabled {{
                background: {C['muted']};
                color: {C['subtext']};
            }}
        """)

    def add_shadow(self, color=None, blur=18):
        s = QGraphicsDropShadowEffect(self)
        s.setBlurRadius(blur)
        s.setOffset(0, 3)
        s.setColor(QColor(color or "#7c5cfc80"))
        self.setGraphicsEffect(s)


class SectionCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 14px;
            }}
        """)
        s = QGraphicsDropShadowEffect(self)
        s.setBlurRadius(40)
        s.setOffset(0, 8)
        s.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(s)


class FieldLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            color: {C['subtext']};
            font-family: "Segoe UI", sans-serif;
            font-size: 10px;
            font-weight: 600;
            background: transparent;
        """)


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {C['border']}; border: none;")


class StatusDot(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._blink  = True
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._do_blink)
        self.set_status(False)

    def set_status(self, active: bool):
        self._active = active
        if active:
            self._timer.start(1200)
        else:
            self._timer.stop()
        self._render(C['success'] if active else C['danger'])

    def _do_blink(self):
        self._blink = not self._blink
        self._render(C['success'] if self._blink else "#2a8060")

    def _render(self, color: str):
        label = "Active" if self._active else "Stopped"
        self.setText(f"●  Watcher: {label}")
        self.setStyleSheet(f"""
            color: {color};
            font-family: "Segoe UI Semibold", sans-serif;
            font-size: 11px;
            font-weight: 600;
            background: transparent;
            padding: 4px 12px;
        """)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════

class AppLockerWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._watcher_proc = None
        self._setup_window()
        self._build_ui()
        self._refresh_table()
        self._start_watcher()

    def _setup_window(self):
        self.setWindowTitle("App Locker  –  Control Panel")
        self.resize(980, 700)
        self.setMinimumSize(820, 580)
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        self._root = QVBoxLayout(central)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

    def _build_ui(self):
        self._build_titlebar()
        self._build_body()
        self._build_statusbar()

    # ── Title bar ─────────────────────────────────────────────────────────────
    def _build_titlebar(self):
        bar = QWidget()
        bar.setFixedHeight(60)
        bar.setStyleSheet(f"""
            QWidget {{
                background: {C['surface']};
                border-bottom: 1px solid {C['border']};
            }}
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 0, 24, 0)

        logo = QLabel("🔐")
        logo.setStyleSheet("font-size: 22px; background: transparent;")

        title = QLabel("App Locker")
        title.setStyleSheet(f"""
            color: {C['text']};
            font-family: "Segoe UI Semibold", sans-serif;
            font-size: 17px;
            font-weight: 700;
            background: transparent;
        """)

        sub = QLabel("Control Panel")
        sub.setStyleSheet(f"""
            color: {C['subtext']};
            font-size: 11px;
            background: transparent;
            margin-top: 4px;
            margin-left: 4px;
        """)

        lay.addWidget(logo)
        lay.addSpacing(8)
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addStretch()

        self._status_dot = StatusDot()
        lay.addWidget(self._status_dot)
        self._root.addWidget(bar)

    # ── Body ──────────────────────────────────────────────────────────────────
    def _build_body(self):
        body = QWidget()
        body.setStyleSheet(f"background: {C['bg']};")
        lay = QHBoxLayout(body)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)
        lay.addWidget(self._build_form_panel(), stretch=0)
        lay.addWidget(self._build_table_panel(), stretch=1)
        self._root.addWidget(body, stretch=1)

    # ── Form panel ────────────────────────────────────────────────────────────
    def _build_form_panel(self):
        card = SectionCard()
        card.setFixedWidth(308)
        vlay = QVBoxLayout(card)
        vlay.setContentsMargins(22, 22, 22, 22)
        vlay.setSpacing(0)

        h = QLabel("Lock New App")
        h.setStyleSheet(f"color:{C['text']}; font-family:'Segoe UI Semibold'; font-size:14px; font-weight:700; background:transparent;")
        vlay.addWidget(h)
        vlay.addSpacing(3)

        s = QLabel("Select an executable and set a password")
        s.setStyleSheet(f"color:{C['subtext']}; font-size:10px; background:transparent;")
        vlay.addWidget(s)
        vlay.addSpacing(16)
        vlay.addWidget(Divider())
        vlay.addSpacing(18)

        # Path
        vlay.addWidget(FieldLabel("EXECUTABLE PATH"))
        vlay.addSpacing(5)
        pr = QHBoxLayout(); pr.setSpacing(6)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("C:\\Program Files\\App.exe")
        self._path_edit.textChanged.connect(self._sync_name)
        pr.addWidget(self._path_edit)
        bb = GlowButton("Browse", C["accent"], C["accent_hover"])
        bb.setFixedWidth(72); bb.clicked.connect(self._browse_file)
        pr.addWidget(bb)
        vlay.addLayout(pr)
        vlay.addSpacing(14)

        # Name
        vlay.addWidget(FieldLabel("APP NAME  (auto-filled)"))
        vlay.addSpacing(5)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("App.exe")
        vlay.addWidget(self._name_edit)
        vlay.addSpacing(14)

        # Password
        vlay.addWidget(FieldLabel("PASSWORD"))
        vlay.addSpacing(5)
        self._pw_edit = QLineEdit()
        self._pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw_edit.setPlaceholderText("Min 4 characters")
        vlay.addWidget(self._pw_edit)
        vlay.addSpacing(14)

        # Confirm
        vlay.addWidget(FieldLabel("CONFIRM PASSWORD"))
        vlay.addSpacing(5)
        self._pw2_edit = QLineEdit()
        self._pw2_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw2_edit.setPlaceholderText("Repeat password")
        vlay.addWidget(self._pw2_edit)
        vlay.addSpacing(22)

        # Lock button
        lb = GlowButton("🔒   Lock This App", C["accent"], C["accent_hover"])
        lb.setFixedHeight(44); lb.add_shadow(); lb.clicked.connect(self._lock_app)
        vlay.addWidget(lb)

        vlay.addSpacing(22)
        vlay.addWidget(Divider())
        vlay.addSpacing(16)

        wl = QLabel("WATCHER SERVICE")
        wl.setStyleSheet(f"color:{C['subtext']}; font-family:'Segoe UI Semibold'; font-size:10px; font-weight:600; background:transparent;")
        vlay.addWidget(wl)
        vlay.addSpacing(8)

        cr = QHBoxLayout(); cr.setSpacing(8)
        stb = GlowButton("▶  Start", C["success"], C["success_hover"])
        stb.setFixedHeight(36); stb.clicked.connect(self._start_watcher)
        spb = GlowButton("■  Stop",  C["danger"],  C["danger_hover"])
        spb.setFixedHeight(36); spb.clicked.connect(self._stop_watcher)
        cr.addWidget(stb); cr.addWidget(spb)
        vlay.addLayout(cr)
        vlay.addStretch()
        return card

    # ── Table panel ───────────────────────────────────────────────────────────
    def _build_table_panel(self):
        card = SectionCard()
        vlay = QVBoxLayout(card)
        vlay.setContentsMargins(20, 18, 20, 16)
        vlay.setSpacing(0)

        hrow = QHBoxLayout()
        ht = QLabel("Locked Applications")
        ht.setStyleSheet(f"color:{C['text']}; font-family:'Segoe UI Semibold'; font-size:14px; font-weight:700; background:transparent;")
        hrow.addWidget(ht)
        hrow.addStretch()

        self._count_badge = QLabel("0 apps")
        self._count_badge.setStyleSheet(f"background:{C['surface2']}; color:{C['subtext']}; font-size:10px; border-radius:8px; padding:3px 10px;")
        hrow.addWidget(self._count_badge)
        hrow.addSpacing(10)

        rfb = QPushButton("↻  Refresh")
        rfb.setFixedHeight(32)
        rfb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        rfb.setStyleSheet(f"""
            QPushButton {{
                background:{C['surface2']}; color:{C['subtext']};
                border:1px solid {C['border']}; border-radius:8px;
                padding:0 14px; font-family:"Segoe UI Semibold"; font-size:11px;
            }}
            QPushButton:hover {{ background:{C['border']}; color:{C['text']}; }}
        """)
        rfb.clicked.connect(self._refresh_table)
        hrow.addWidget(rfb)
        hrow.addSpacing(8)

        rmb = GlowButton("🗑  Remove Selected", C["danger"], C["danger_hover"])
        rmb.setFixedHeight(32); rmb.clicked.connect(self._remove_app)
        hrow.addWidget(rmb)

        vlay.addLayout(hrow)
        vlay.addSpacing(14)
        vlay.addWidget(Divider())
        vlay.addSpacing(10)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["App Name", "Path", "Date Added", "Status"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setShowGrid(True)
        self._table.setAlternatingRowColors(True)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setDefaultSectionSize(38)

        vlay.addWidget(self._table)
        return card

    # ── Status bar ────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = QWidget()
        bar.setFixedHeight(30)
        bar.setStyleSheet(f"QWidget {{ background:{C['surface']}; border-top:1px solid {C['border']}; }}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)

        self._status_lbl = QLabel("Ready.")
        self._status_lbl.setStyleSheet(f"color:{C['subtext']}; font-family:'Consolas',monospace; font-size:10px; background:transparent;")
        lay.addWidget(self._status_lbl)
        lay.addStretch()

        ver = QLabel("App Locker  v2.0  (PyQt6)")
        ver.setStyleSheet(f"color:{C['muted']}; font-size:10px; background:transparent;")
        lay.addWidget(ver)
        self._root.addWidget(bar)

    # ══════════════════════════════════════════════════════════════════════════
    #  CALLBACKS
    # ══════════════════════════════════════════════════════════════════════════

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Executable", "C:\\",
                                              "Executables (*.exe);;All Files (*.*)")
        if path:
            self._path_edit.setText(path)

    def _sync_name(self, path):
        if path:
            self._name_edit.setText(os.path.basename(path))

    def _lock_app(self):
        path = self._path_edit.text().strip()
        name = self._name_edit.text().strip()
        pw   = self._pw_edit.text()
        pw2  = self._pw2_edit.text()

        if not path:            return self._alert("Please select an executable path.")
        if not os.path.isfile(path): return self._alert(f"File not found:\n{path}")
        if not name:            return self._alert("App name cannot be empty.")
        if not pw:              return self._alert("Password cannot be empty.")
        if len(pw) < 4:         return self._alert("Password must be at least 4 characters.")
        if pw != pw2:           return self._alert("Passwords do not match.")

        if add_locked_app(name, path, pw):
            logger.info(f"GUI locked app: {name} -> {path}")
            self._info(f"✓  '{normalise_name(name)}' is now locked.")
            self._refresh_table()
            self._path_edit.clear(); self._name_edit.clear()
            self._pw_edit.clear();   self._pw2_edit.clear()
        else:
            self._alert("Failed to save config. Check logs.")

    def _remove_app(self):
        row = self._table.currentRow()
        if row < 0:
            return self._alert("Select an app from the table first.", kind="info")

        appname = self._table.item(row, 0).text()
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Remove Lock")
        dlg.setText(f"Remove lock on  <b>{appname}</b>?")
        dlg.setInformativeText("The app will be freely accessible again.")
        dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dlg.setDefaultButton(QMessageBox.StandardButton.No)
        if dlg.exec() != QMessageBox.StandardButton.Yes:
            return

        if remove_locked_app(appname):
            logger.info(f"GUI removed lock: {appname}")
            self._info(f"✓  '{appname}' removed.")
            self._refresh_table()
        else:
            self._alert(f"Could not remove '{appname}'.")

    def _refresh_table(self):
        self._table.setRowCount(0)
        config = load_config()
        locked = {k: v for k, v in config.items() if v.get("locked", True)}
        self._table.setRowCount(len(locked))

        for i, (name, data) in enumerate(locked.items()):
            added = data.get("added_at", "")[:10]
            path  = data.get("path", "")

            ni = QTableWidgetItem(name)
            pi = QTableWidgetItem(path)
            ai = QTableWidgetItem(added)
            si = QTableWidgetItem("🔒 Locked")
            si.setForeground(QColor(C["danger"]))

            for item in (ni, pi, ai, si):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self._table.setItem(i, 0, ni)
            self._table.setItem(i, 1, pi)
            self._table.setItem(i, 2, ai)
            self._table.setItem(i, 3, si)

        count = len(locked)
        self._count_badge.setText(f"{count} app{'s' if count != 1 else ''}")
        self._info(f"{count} app(s) currently locked.")

    def _start_watcher(self):
        if self._watcher_proc and self._watcher_proc.poll() is None:
            return self._info("Watcher is already running.")
        watcher_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watcher.py")
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            self._watcher_proc = subprocess.Popen(
                [sys.executable, watcher_path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=flags
            )
            self._status_dot.set_status(True)
            logger.info(f"Watcher started (PID {self._watcher_proc.pid})")
            self._info(f"Watcher started  (PID {self._watcher_proc.pid})")
        except Exception as e:
            self._alert(f"Could not start watcher:\n{e}")

    def _stop_watcher(self):
        if self._watcher_proc and self._watcher_proc.poll() is None:
            self._watcher_proc.terminate()
            self._watcher_proc = None
            self._status_dot.set_status(False)
            logger.info("Watcher stopped by user")
            self._info("Watcher stopped.")
        else:
            self._info("Watcher is not running.")

    def _info(self, msg):
        self._status_lbl.setText(msg)

    def _alert(self, msg, kind="error"):
        dlg = QMessageBox(self)
        dlg.setText(msg)
        dlg.setWindowTitle("Error" if kind == "error" else "Info")
        dlg.setIcon(QMessageBox.Icon.Critical if kind == "error" else QMessageBox.Icon.Information)
        dlg.exec()

    def closeEvent(self, event):
        if self._watcher_proc and self._watcher_proc.poll() is None:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Exit")
            dlg.setText("The watcher is still running.")
            dlg.setInformativeText("Stop the watcher and exit?")
            dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            dlg.setDefaultButton(QMessageBox.StandardButton.Yes)
            if dlg.exec() == QMessageBox.StandardButton.Yes:
                self._stop_watcher(); event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("App Locker")
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont("Segoe UI", 10))
    window = AppLockerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()