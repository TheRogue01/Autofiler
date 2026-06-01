"""
main.py — Smart Autonomous File Organization and Monitoring Agent
GUI entry-point built with tkinter (ships with Python, no extra install needed).
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

from organizer import FileOrganizer, undo_last_move, undo_all_moves
from monitor import FolderMonitor
from utils import setup_logger

logger = setup_logger()


# ── Colour Palette ─────────────────────────────────────────────────────────────
BG        = "#1e1e2e"   # dark background
SURFACE   = "#2a2a3e"   # card / panel
ACCENT    = "#7c5cfc"   # purple accent
ACCENT2   = "#00d4aa"   # teal accent
TEXT      = "#cdd6f4"   # main text
TEXT_DIM  = "#6c7086"   # muted text
SUCCESS   = "#a6e3a1"   # green
WARNING   = "#f9e2af"   # yellow
ERROR     = "#f38ba8"   # red
DUPLICATE = "#89dceb"   # cyan


# ── Main Application ───────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart File Organizer Agent")
        self.geometry("900x680")
        self.minsize(750, 550)
        self.configure(bg=BG)

        # State
        self._source_var  = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self._dest_var    = tk.StringVar(value=os.path.join(os.getcwd(), "organized"))
        self._threshold   = tk.DoubleVar(value=500)
        self._monitoring  = tk.BooleanVar(value=False)
        self._organizer: FileOrganizer | None  = None
        self._monitor:   FolderMonitor | None  = None

        self._build_ui()
        self._log("🚀 File Organizer Agent ready.")

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=ACCENT, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="🗂  Smart File Organizer Agent",
                 font=("Segoe UI", 16, "bold"),
                 bg=ACCENT, fg="white").pack()
        tk.Label(header, text="Autonomous • Real-time • Intelligent",
                 font=("Segoe UI", 9),
                 bg=ACCENT, fg="#d0ccff").pack()

        # ── Main layout ──
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        left  = tk.Frame(body, bg=BG, width=300)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_controls(left)
        self._build_log(right)

    def _section(self, parent, title: str) -> tk.Frame:
        """Styled card-style section frame."""
        wrapper = tk.Frame(parent, bg=BG)
        wrapper.pack(fill="x", pady=(0, 10))
        tk.Label(wrapper, text=title.upper(),
                 font=("Segoe UI", 8, "bold"),
                 bg=BG, fg=TEXT_DIM).pack(anchor="w")
        card = tk.Frame(wrapper, bg=SURFACE, padx=12, pady=10,
                        highlightbackground=ACCENT, highlightthickness=1)
        card.pack(fill="x")
        return card

    def _build_controls(self, parent):
        # ── Folders ──
        sec = self._section(parent, "📁  Folders")

        tk.Label(sec, text="Source Folder", font=("Segoe UI", 9),
                 bg=SURFACE, fg=TEXT_DIM).pack(anchor="w")
        row = tk.Frame(sec, bg=SURFACE)
        row.pack(fill="x", pady=(2, 8))
        tk.Entry(row, textvariable=self._source_var, bg="#3a3a50", fg=TEXT,
                 relief="flat", insertbackground=TEXT).pack(side="left", fill="x",
                                                             expand=True, ipady=4)
        self._btn(row, "Browse", self._browse_source, ACCENT).pack(side="left",
                                                                     padx=(4, 0))

        tk.Label(sec, text="Destination Root", font=("Segoe UI", 9),
                 bg=SURFACE, fg=TEXT_DIM).pack(anchor="w")
        row2 = tk.Frame(sec, bg=SURFACE)
        row2.pack(fill="x", pady=(2, 0))
        tk.Entry(row2, textvariable=self._dest_var, bg="#3a3a50", fg=TEXT,
                 relief="flat", insertbackground=TEXT).pack(side="left", fill="x",
                                                             expand=True, ipady=4)
        self._btn(row2, "Browse", self._browse_dest, ACCENT).pack(side="left",
                                                                    padx=(4, 0))

        # ── Settings ──
        sec2 = self._section(parent, "⚙️  Settings")
        tk.Label(sec2, text="Large-file threshold (MB)",
                 font=("Segoe UI", 9), bg=SURFACE, fg=TEXT_DIM).pack(anchor="w")
        scale_row = tk.Frame(sec2, bg=SURFACE)
        scale_row.pack(fill="x", pady=(2, 0))
        tk.Scale(scale_row, from_=50, to=2000, orient="horizontal",
                 variable=self._threshold,
                 bg=SURFACE, fg=TEXT, troughcolor=BG,
                 highlightthickness=0, bd=0,
                 activebackground=ACCENT).pack(side="left", fill="x", expand=True)
        self._threshold_lbl = tk.Label(scale_row,
                                        textvariable=self._threshold,
                                        font=("Segoe UI", 9, "bold"),
                                        bg=SURFACE, fg=ACCENT, width=6)
        self._threshold_lbl.pack(side="left")

        # ── Actions ──
        sec3 = self._section(parent, "▶  Actions")

        self._btn(sec3, "Organise Now", self._run_organise, ACCENT2,
                  full=True).pack(fill="x", pady=(0, 6))

        monitor_frame = tk.Frame(sec3, bg=SURFACE)
        monitor_frame.pack(fill="x", pady=(0, 6))
        self._start_btn = self._btn(monitor_frame, "▶ Start Monitor",
                                     self._start_monitor, SUCCESS)
        self._start_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._stop_btn  = self._btn(monitor_frame, "■ Stop Monitor",
                                     self._stop_monitor, ERROR, state="disabled")
        self._stop_btn.pack(side="left", fill="x", expand=True)

        undo_frame = tk.Frame(sec3, bg=SURFACE)
        undo_frame.pack(fill="x")
        self._btn(undo_frame, "↩ Undo Last", self._undo_last, WARNING).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        self._btn(undo_frame, "↩↩ Undo All", self._undo_all, WARNING).pack(
            side="left", fill="x", expand=True)

        # ── Cleanup ──
        sec4 = self._section(parent, "🧹  Maintenance")
        self._btn(sec4, "Remove Empty Folders", self._cleanup, ACCENT,
                  full=True).pack(fill="x")

        # ── Status indicator ──
        self._status_lbl = tk.Label(parent, text="● IDLE",
                                     font=("Segoe UI", 9, "bold"),
                                     bg=BG, fg=TEXT_DIM)
        self._status_lbl.pack(anchor="w", pady=(6, 0))

    def _build_log(self, parent):
        tk.Label(parent, text="ACTIVITY LOG",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG, fg=TEXT_DIM).pack(anchor="w")
        self._log_box = scrolledtext.ScrolledText(
            parent, bg=SURFACE, fg=TEXT,
            font=("Consolas", 9), relief="flat",
            wrap="word", state="disabled",
            insertbackground=TEXT,
            highlightthickness=1, highlightbackground=ACCENT
        )
        self._log_box.pack(fill="both", expand=True, pady=(4, 6))

        # Colour tags
        for tag, colour in [
            ("moved", SUCCESS), ("duplicate", DUPLICATE),
            ("skipped", TEXT_DIM), ("error", ERROR),
            ("info", TEXT), ("warn", WARNING),
        ]:
            self._log_box.tag_config(tag, foreground=colour)

        # Clear log button
        self._btn(parent, "Clear Log", self._clear_log, TEXT_DIM,
                  full=True).pack(fill="x")

    # ── Widget helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _btn(parent, text, command, colour, full=False, state="normal") -> tk.Button:
        return tk.Button(
            parent, text=text, command=command,
            bg=colour, fg="white" if colour not in (TEXT_DIM, WARNING) else BG,
            font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2",
            activebackground=colour, activeforeground="white",
            padx=8, pady=6, state=state,
        )

    # ── Logging ────────────────────────────────────────────────────────────────

    def _log(self, message: str, tag: str = "info"):
        """Append a timestamped message to the log box (thread-safe via after)."""
        def _append():
            self._log_box.configure(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_box.insert("end", f"[{ts}] {message}\n", tag)
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        self.after(0, _append)

    def _log_result(self, message: str):
        """Detect tag from result message prefix."""
        low = message.lower()
        if "moved"      in low: tag = "moved"
        elif "duplicate" in low: tag = "duplicate"
        elif "ignored"  in low: tag = "skipped"
        elif "error"    in low: tag = "error"
        elif "warn"     in low: tag = "warn"
        else:                   tag = "info"
        self._log(message, tag)

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    # ── Status ─────────────────────────────────────────────────────────────────

    def _set_status(self, text: str, colour: str):
        self._status_lbl.configure(text=text, fg=colour)

    # ── Browse ─────────────────────────────────────────────────────────────────

    def _browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self._source_var.set(folder)

    def _browse_dest(self):
        folder = filedialog.askdirectory(title="Select Destination Root")
        if folder:
            self._dest_var.set(folder)

    # ── Organiser ──────────────────────────────────────────────────────────────

    def _make_organizer(self) -> FileOrganizer:
        return FileOrganizer(
            source_folder=self._source_var.get(),
            dest_root=self._dest_var.get(),
            large_file_threshold_mb=self._threshold.get(),
        )

    def _run_organise(self):
        organizer = self._make_organizer()
        self._log(f"Organising '{organizer.source_folder}' …", "info")
        self._set_status("● WORKING", WARNING)
        self.update_idletasks()

        summary = organizer.organize_folder()

        self._log(
            f"✔ Done — moved: {summary['moved']}  duplicates: {summary['duplicates']}  "
            f"skipped: {summary['skipped']}  errors: {summary['errors']}",
            "moved"
        )
        self._set_status("● IDLE", TEXT_DIM)

    # ── Monitor ────────────────────────────────────────────────────────────────

    def _start_monitor(self):
        if self._monitor and self._monitor.is_running:
            return

        self._organizer = self._make_organizer()
        self._monitor   = FolderMonitor(
            self._organizer,
            on_event_callback=self._log_result,
        )
        self._monitor.start()

        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._set_status("● MONITORING", SUCCESS)
        self._log(f"👁 Monitoring '{self._organizer.source_folder}' …", "info")

    def _stop_monitor(self):
        if self._monitor:
            self._monitor.stop()
            self._monitor = None
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._set_status("● IDLE", TEXT_DIM)
        self._log("Monitor stopped.", "info")

    # ── Undo ───────────────────────────────────────────────────────────────────

    def _undo_last(self):
        msg = undo_last_move()
        self._log(msg, "warn")

    def _undo_all(self):
        if not messagebox.askyesno("Undo All", "Restore ALL moved files?"):
            return
        count = undo_all_moves()
        self._log(f"↩ Undone {count} move(s).", "warn")

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def _cleanup(self):
        organizer = self._make_organizer()
        removed   = organizer.cleanup_empty_folders()
        self._log(f"🧹 Removed {removed} empty folder(s).", "info")

    # ── Window close ──────────────────────────────────────────────────────────

    def on_close(self):
        if self._monitor and self._monitor.is_running:
            self._monitor.stop()
        self.destroy()


# ── Entry-point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
