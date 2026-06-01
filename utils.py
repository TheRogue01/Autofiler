import os
import hashlib
import logging
from datetime import datetime

# ── Logging Setup ──────────────────────────────────────────────────────────────

def setup_logger(log_dir: str = "logs") -> logging.Logger:
    """Create a logger that writes to both a file and the console."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"organizer_{datetime.now().strftime('%Y%m%d')}.log")

    logger = logging.getLogger("FileOrganizer")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s — %(message)s",
                                          datefmt="%H:%M:%S"))
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


# ── Duplicate Detection ────────────────────────────────────────────────────────

def file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """Return the MD5 hash of a file's contents."""
    h = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
    except (OSError, IOError):
        return ""
    return h.hexdigest()


def is_duplicate(filepath: str, destination_folder: str) -> str | None:
    """
    Check whether an identical file (by hash) already exists in destination_folder.
    Returns the path of the existing duplicate, or None if no duplicate found.
    """
    if not os.path.isdir(destination_folder):
        return None

    incoming_hash = file_hash(filepath)
    if not incoming_hash:
        return None

    for existing in os.listdir(destination_folder):
        existing_path = os.path.join(destination_folder, existing)
        if os.path.isfile(existing_path) and file_hash(existing_path) == incoming_hash:
            return existing_path
    return None


# ── Large File Detection ───────────────────────────────────────────────────────

def is_large_file(filepath: str, threshold_mb: float = 500) -> bool:
    """Return True if the file exceeds the given size threshold (default 500 MB)."""
    try:
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        return size_mb >= threshold_mb
    except OSError:
        return False


def human_size(filepath: str) -> str:
    """Return a human-readable file size string."""
    try:
        size = os.path.getsize(filepath)
    except OSError:
        return "unknown size"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
