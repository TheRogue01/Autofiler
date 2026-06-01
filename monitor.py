import os
import time
import threading
from utils import setup_logger

logger = setup_logger()

# ── Watchdog import with graceful fallback ─────────────────────────────────────
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("watchdog not installed — falling back to polling monitor. "
                   "Run:  pip install watchdog")


# ── Watchdog-based handler ─────────────────────────────────────────────────────

class _OrganizerHandler(FileSystemEventHandler):
    """Reacts to new files dropped into the watched folder."""

    def __init__(self, organizer, on_event_callback=None):
        super().__init__()
        self.organizer = organizer
        self.on_event_callback = on_event_callback
        self._seen: set[str] = set()   # avoid double-processing

    def on_created(self, event: FileCreatedEvent):
        if event.is_directory:
            return

        filepath = event.src_path
        if filepath in self._seen:
            return
        self._seen.add(filepath)

        # Short delay — let the OS finish writing the file
        time.sleep(0.5)

        result = self.organizer.organize_file(filepath)
        if self.on_event_callback:
            self.on_event_callback(result["message"])

    def on_moved(self, event):
        """Also handle files moved/renamed into the folder."""
        if event.is_directory:
            return
        filepath = event.dest_path
        if filepath in self._seen:
            return
        self._seen.add(filepath)
        time.sleep(0.3)
        result = self.organizer.organize_file(filepath)
        if self.on_event_callback:
            self.on_event_callback(result["message"])


# ── Polling fallback (no watchdog) ────────────────────────────────────────────

class _PollingHandler:
    """Watches a folder by comparing snapshots every `interval` seconds."""

    def __init__(self, organizer, interval: float = 2.0, on_event_callback=None):
        self.organizer           = organizer
        self.interval            = interval
        self.on_event_callback   = on_event_callback
        self._known_files: set[str] = set()
        self._running            = False
        self._thread: threading.Thread | None = None

    def _scan(self) -> set[str]:
        folder = self.organizer.source_folder
        if not os.path.isdir(folder):
            return set()
        return {
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f))
        }

    def _loop(self):
        self._known_files = self._scan()
        while self._running:
            time.sleep(self.interval)
            current = self._scan()
            new_files = current - self._known_files
            for filepath in new_files:
                time.sleep(0.3)
                result = self.organizer.organize_file(filepath)
                if self.on_event_callback:
                    self.on_event_callback(result["message"])
            self._known_files = self._scan()   # refresh after organising

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"[Polling] Watching '{self.organizer.source_folder}' every "
                    f"{self.interval}s")

    def stop(self):
        self._running = False
        logger.info("[Polling] Monitor stopped.")


# ── Public Monitor class ───────────────────────────────────────────────────────

class FolderMonitor:
    """
    Watches a folder and automatically organises files as they appear.

    Usage:
        monitor = FolderMonitor(organizer)
        monitor.start()
        ...
        monitor.stop()
    """

    def __init__(self, organizer, on_event_callback=None):
        self.organizer         = organizer
        self.on_event_callback = on_event_callback
        self._observer         = None
        self._polling          = None

    @property
    def is_running(self) -> bool:
        if WATCHDOG_AVAILABLE and self._observer:
            return self._observer.is_alive()
        if self._polling:
            return self._polling._running
        return False

    def start(self):
        if self.is_running:
            logger.warning("Monitor is already running.")
            return

        folder = self.organizer.source_folder
        if not os.path.isdir(folder):
            logger.error(f"Cannot monitor non-existent folder: {folder}")
            return

        if WATCHDOG_AVAILABLE:
            handler = _OrganizerHandler(self.organizer, self.on_event_callback)
            self._observer = Observer()
            self._observer.schedule(handler, folder, recursive=False)
            self._observer.start()
            logger.info(f"[Watchdog] Monitoring '{folder}'")
        else:
            self._polling = _PollingHandler(
                self.organizer, on_event_callback=self.on_event_callback
            )
            self._polling.start()

    def stop(self):
        if WATCHDOG_AVAILABLE and self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("[Watchdog] Monitor stopped.")
        elif self._polling:
            self._polling.stop()
            self._polling = None
