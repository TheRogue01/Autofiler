import os
import shutil
import json
from pathlib import Path
from utils import setup_logger, is_duplicate, is_large_file, human_size

logger = setup_logger()

# ── Category Definitions ───────────────────────────────────────────────────────

CATEGORIES: dict[str, list[str]] = {
    "Images":     [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
                   ".tiff", ".ico", ".heic", ".raw"],
    "Documents":  [".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md",
                   ".ppt", ".pptx", ".xls", ".xlsx", ".csv"],
    "Videos":     [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
                   ".m4v", ".mpeg", ".3gp"],
    "Music":      [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma",
                   ".opus"],
    "Archives":   [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
                   ".iso", ".dmg"],
    "Code":       [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp",
                   ".c", ".h", ".cs", ".go", ".rs", ".rb", ".php", ".swift",
                   ".kt", ".sh", ".bat", ".json", ".xml", ".yaml", ".yml"],
    "Executables":[".exe", ".msi", ".apk", ".deb", ".rpm", ".app"],
}

# ── Smart / AI Keyword Categorization ─────────────────────────────────────────
# Maps lowercase keywords found in the filename to a sub-folder inside Documents.

SMART_RULES: dict[str, list[str]] = {
    "Work":    ["invoice", "contract", "proposal", "report", "meeting",
                "presentation", "budget", "project", "client", "company"],
    "Study":   ["homework", "assignment", "lecture", "notes", "exam",
                "quiz", "study", "thesis", "essay", "school", "class"],
    "Finance": ["invoice", "receipt", "bank", "statement", "tax",
                "finance", "payment", "salary", "expense", "bill"],
    "Personal":["resume", "cv", "portfolio", "id", "passport",
                "certificate", "license", "profile"],
}


def classify_file(filepath: str, large_file_threshold_mb: float = 500) -> str:
    """
    Return the destination category folder name for a given file.
    Priority: LargeFiles > extension match > Others.
    """
    if is_large_file(filepath, large_file_threshold_mb):
        return "LargeFiles"

    ext = Path(filepath).suffix.lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"


def smart_subcategory(filename: str, base_category: str) -> str | None:
    """
    For files landing in Documents, attempt keyword-based sub-categorisation.
    Returns the sub-folder name, or None if no keyword matched.
    """
    if base_category != "Documents":
        return None

    name_lower = filename.lower()
    for subfolder, keywords in SMART_RULES.items():
        for kw in keywords:
            if kw in name_lower:
                return subfolder
    return None


# ── Undo History ───────────────────────────────────────────────────────────────

UNDO_FILE = "undo_history.json"

def _load_undo_history() -> list[dict]:
    if os.path.exists(UNDO_FILE):
        try:
            with open(UNDO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_undo_history(history: list[dict]) -> None:
    with open(UNDO_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def record_move(source: str, destination: str) -> None:
    history = _load_undo_history()
    history.append({"src": source, "dst": destination})
    _save_undo_history(history)


def undo_last_move() -> str:
    """Undo the most recent file move. Returns a status message."""
    history = _load_undo_history()
    if not history:
        return "Nothing to undo."

    last = history.pop()
    src, dst = last["src"], last["dst"]

    if not os.path.exists(dst):
        _save_undo_history(history)
        return f"Cannot undo — file not found at: {dst}"

    try:
        os.makedirs(os.path.dirname(src), exist_ok=True)
        shutil.move(dst, src)
        _save_undo_history(history)
        msg = f"Undo: moved '{os.path.basename(dst)}' back to '{os.path.dirname(src)}'"
        logger.info(msg)
        return msg
    except Exception as e:
        return f"Undo failed: {e}"


def undo_all_moves() -> int:
    """Undo every recorded move. Returns the count of successful undos."""
    history = _load_undo_history()
    count = 0
    for entry in reversed(history):
        src, dst = entry["src"], entry["dst"]
        if os.path.exists(dst):
            try:
                os.makedirs(os.path.dirname(src), exist_ok=True)
                shutil.move(dst, src)
                logger.info(f"Undo: '{os.path.basename(dst)}' → '{os.path.dirname(src)}'")
                count += 1
            except Exception as e:
                logger.error(f"Undo failed for '{dst}': {e}")
    _save_undo_history([])
    return count


# ── Core Organizer ─────────────────────────────────────────────────────────────

class FileOrganizer:
    """
    Scans a source folder and moves every file into categorised sub-folders
    inside the destination root.
    """

    def __init__(self,
                 source_folder: str,
                 dest_root: str = "organized",
                 large_file_threshold_mb: float = 500):
        self.source_folder = os.path.abspath(source_folder)
        self.dest_root     = os.path.abspath(dest_root)
        self.threshold_mb  = large_file_threshold_mb

    # ── internal helpers ──

    def _dest_for(self, filepath: str) -> str:
        """Build the full destination path for a file."""
        category = classify_file(filepath, self.threshold_mb)
        sub = smart_subcategory(os.path.basename(filepath), category)

        if sub:
            folder = os.path.join(self.dest_root, category, sub)
        else:
            folder = os.path.join(self.dest_root, category)

        os.makedirs(folder, exist_ok=True)
        return folder

    def _unique_dest_path(self, folder: str, filename: str) -> str:
        """
        Ensure we never silently overwrite a file with a different name.
        Appends (1), (2), … if the target already exists.
        """
        base, ext = os.path.splitext(filename)
        candidate = os.path.join(folder, filename)
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(folder, f"{base} ({counter}){ext}")
            counter += 1
        return candidate

    # ── public API ──

    def organize_file(self, filepath: str) -> dict:
        """
        Move a single file.  Returns a result dict with keys:
        status  → 'moved' | 'duplicate' | 'skipped' | 'error'
        message → human-readable description
        """
        if not os.path.isfile(filepath):
            return {"status": "skipped", "message": f"Not a file: {filepath}"}

        filename = os.path.basename(filepath)

        # Skip hidden / temp files
        if filename.startswith(".") or filename.endswith(".tmp"):
            return {"status": "skipped", "message": f"Ignored temp/hidden: {filename}"}

        dest_folder = self._dest_for(filepath)

        # Duplicate check
        dup = is_duplicate(filepath, dest_folder)
        if dup:
            dup_folder = os.path.join(self.dest_root, "Duplicates")
            os.makedirs(dup_folder, exist_ok=True)
            dest_path = self._unique_dest_path(dup_folder, filename)
            shutil.move(filepath, dest_path)
            record_move(filepath, dest_path)
            msg = (f"Duplicate detected — '{filename}' moved to Duplicates "
                   f"(original: '{os.path.basename(dup)}')")
            logger.warning(msg)
            return {"status": "duplicate", "message": msg}

        dest_path = self._unique_dest_path(dest_folder, filename)

        try:
            shutil.move(filepath, dest_path)
            record_move(filepath, dest_path)
            category = os.path.relpath(dest_folder, self.dest_root)
            size     = human_size(dest_path)
            msg = f"Moved '{filename}' → {category}  [{size}]"
            logger.info(msg)
            return {"status": "moved", "message": msg}
        except Exception as e:
            msg = f"Error moving '{filename}': {e}"
            logger.error(msg)
            return {"status": "error", "message": msg}

    def organize_folder(self) -> dict:
        """
        Scan the entire source folder and organise all files.
        Returns a summary dict.
        """
        if not os.path.isdir(self.source_folder):
            logger.error(f"Source folder not found: {self.source_folder}")
            return {"moved": 0, "duplicates": 0, "skipped": 0, "errors": 0}

        summary = {"moved": 0, "duplicates": 0, "skipped": 0, "errors": 0}
        logger.info(f"── Organising '{self.source_folder}' ──")

        for entry in os.scandir(self.source_folder):
            if entry.is_file(follow_symlinks=False):
                result = self.organize_file(entry.path)
                if result["status"] == "moved":
                    summary["moved"] += 1
                elif result["status"] == "duplicate":
                    summary["duplicates"] += 1
                elif result["status"] == "skipped":
                    summary["skipped"] += 1
                else:
                    summary["errors"] += 1

        logger.info(
            f"── Done — moved: {summary['moved']}, duplicates: {summary['duplicates']}, "
            f"skipped: {summary['skipped']}, errors: {summary['errors']} ──"
        )
        return summary

    def cleanup_empty_folders(self) -> int:
        """Remove empty sub-folders inside the source directory. Returns count removed."""
        removed = 0
        for dirpath, dirnames, filenames in os.walk(self.source_folder, topdown=False):
            if dirpath == self.source_folder:
                continue
            if not os.listdir(dirpath):
                try:
                    os.rmdir(dirpath)
                    logger.info(f"Removed empty folder: {dirpath}")
                    removed += 1
                except OSError:
                    pass
        return removed
