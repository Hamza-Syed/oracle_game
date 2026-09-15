"""Session state and JSON persistence for The Oracle."""

from collections import Counter
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from personalities import PERSONALITY_NAMES


def is_valid_string(value):
    """Reject empty, non-text, or broken Unicode entries from a save."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def valid_strings(value):
    """Keep usable entries without converting invalid values into game data."""
    if not isinstance(value, list):
        return []
    return [item for item in value if is_valid_string(item)]


def nonnegative_integer(value):
    # bool is an int subclass, but True is not a meaningful question count.
    return value if type(value) is int and value >= 0 else 0


def default_memory_path():
    """Frozen builds use user storage, never PyInstaller's bundled resources."""
    if getattr(sys, "frozen", False):
        local_data = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local_data) if local_data else Path.home() / "AppData" / "Local"
        return base / "TheOracle" / "memory.json"
    return Path(__file__).with_name("memory.json")


class Memory:
    def __init__(self, path=None):
        # Keep the save beside the game even when launched from another folder.
        self.path = Path(path) if path is not None else default_memory_path()
        if path is None and getattr(sys, "frozen", False):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.questions_asked = 0
        self.question_history = []
        self.repeat_count = {}
        self.achievements = set()
        self.used_personalities = set()
        self.load_memory()
        # A boundary into the existing history, not another copy of it.
        self.previous_session_question_count = len(self.question_history)

    @staticmethod
    def normalize_question(question):
        return " ".join(question.casefold().split())

    def remember_question(self, question):
        self.questions_asked += 1
        self.question_history.append(question)

    def get_question_count(self):
        return self.questions_asked

    def has_asked_before(self, question):
        normalized = self.normalize_question(question)
        # Recovery can retain repeat counts even when history is incomplete.
        if normalized in self.repeat_count:
            return True
        return any(self.normalize_question(previous) == normalized
                   for previous in self.question_history)

    def track_repeat(self, question):
        normalized = self.normalize_question(question)
        self.repeat_count[normalized] = self.repeat_count.get(normalized, 0) + 1
        return self.repeat_count[normalized]

    def has_asked_in_previous_session(self, question):
        # This discovery needs surviving history from startup, not inferred data.
        normalized = self.normalize_question(question)
        return any(
            self.normalize_question(self.question_history[index]) == normalized
            for index in range(self.previous_session_question_count)
        )

    def get_recent_question(self):
        return self.question_history[-1] if self.question_history else None

    @staticmethod
    def detect_topic(question):
        words = set(re.findall(r"\b\w+\b", question.casefold()))
        if words & {"exam", "exams", "test", "tests", "study", "studying"}:
            return "exam"
        if words & {"internship", "internships", "intern"}:
            return "internship"
        if words & {"job", "jobs", "career", "employment", "interview"}:
            return "job"
        return "other"

    def get_favorite_topic(self):
        topics = Counter(self.detect_topic(question) for question in self.question_history)
        topics.pop("other", None)
        return topics.most_common(1)[0][0] if topics else "unknown"

    def save_memory(self):
        data = {
            "questions_asked": self.questions_asked,
            "question_history": self.question_history,
            "repeat_count": self.repeat_count,
            "achievements": sorted(self.achievements),
            "used_personalities": sorted(self.used_personalities),
        }
        # Same directory means replacement stays on the same filesystem.
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=self.path.name + ".", suffix=".tmp", delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(data, temporary, indent=4, ensure_ascii=False, allow_nan=False)
                temporary.flush()
                os.fsync(temporary.fileno())
            # Close before replacing: required on Windows.
            temporary_path.replace(self.path)
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    # A leftover temporary file is preferable to losing the save.
                    pass

    def backup_corrupt_save(self, contents):
        """Preserve original bytes under an unused name before allowing recovery."""
        number = 0
        while True:
            suffix = "" if number == 0 else f".{number}"
            backup = self.path.with_name(f"{self.path.stem}.corrupt{suffix}.json")
            try:
                # Exclusive creation never overwrites an earlier backup.
                with backup.open("xb") as file:
                    file.write(contents)
                    file.flush()
                    os.fsync(file.fileno())
                return
            except FileExistsError:
                number += 1
            # Other I/O errors propagate. Startup stops rather than overwrite
            # a damaged save whose backup could not be completed.

    def load_memory(self):
        try:
            contents = self.path.read_bytes()
        except FileNotFoundError:
            return
        try:
            # Decode explicitly; retain original bytes for lossless backups.
            data = json.loads(contents.decode("utf-8").lstrip("\ufeff"))
            if not isinstance(data, dict):
                raise ValueError("Memory must be a JSON object.")
        except (UnicodeDecodeError, ValueError):
            self.backup_corrupt_save(contents)
            data = {}

        self.question_history = valid_strings(data.get("question_history", []))
        stored_count = nonnegative_integer(data.get("questions_asked", 0))
        # Preserve a valid lifetime count even if history is incomplete. History
        # can prove a lower count stale, but we do not manufacture missing entries.
        self.questions_asked = max(stored_count, len(self.question_history))
        self.repeat_count = {}
        stored_repeats = data.get("repeat_count", {})
        if isinstance(stored_repeats, dict):
            for question, count in stored_repeats.items():
                if is_valid_string(question) and nonnegative_integer(count) > 0:
                    key = self.normalize_question(question)
                    self.repeat_count[key] = max(self.repeat_count.get(key, 0), count)
        # Repair stale/missing repeat counters using evidence in surviving history.
        history_counts = Counter(self.normalize_question(q) for q in self.question_history)
        for question, count in history_counts.items():
            self.repeat_count[question] = max(self.repeat_count.get(question, 0), count)
        self.achievements = set(valid_strings(data.get("achievements", [])))
        self.used_personalities = set(valid_strings(data.get("used_personalities", []))) & set(PERSONALITY_NAMES)
