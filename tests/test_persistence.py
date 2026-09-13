import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
import game as engine
import memories
from memories import Memory


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory / "memory.json"
        self.data = {
            "questions_asked": 2,
            "question_history": ["A question?", "Another question?"],
            "repeat_count": {"a question?": 1, "another question?": 1},
            "achievements": ["First Question"],
            "used_personalities": ["sage"],
        }

    def write(self, data):
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return Memory(self.path)

    def assert_defaults(self, memory):
        self.assertEqual(memory.questions_asked, 0)
        self.assertEqual(memory.question_history, [])
        self.assertEqual(memory.repeat_count, {})
        self.assertEqual(memory.achievements, set())
        self.assertEqual(memory.used_personalities, set())
        self.assertEqual(memory.previous_session_question_count, 0)

    def test_missing_file_starts_quietly_without_creating_save(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            memory = Memory(self.path)
        self.assert_defaults(memory)
        self.assertEqual(output.getvalue(), "")
        self.assertFalse(self.path.exists())
        memory.save_memory()
        self.assertTrue(self.path.exists())

    def test_empty_file_recovers(self):
        self.path.write_bytes(b"")
        self.assert_defaults(Memory(self.path))
        self.assertEqual((self.directory / "memory.corrupt.json").read_bytes(), b"")

    def test_whitespace_only_file_recovers(self):
        self.path.write_text(" \n\t ", encoding="utf-8")
        self.assert_defaults(Memory(self.path))

    def test_malformed_json_is_backed_up_before_next_save(self):
        original = b'{"question_history": ["unfinished'
        self.path.write_bytes(original)
        memory = Memory(self.path)
        self.assert_defaults(memory)
        self.assertEqual(self.path.read_bytes(), original)
        backup = self.directory / "memory.corrupt.json"
        self.assertEqual(backup.read_bytes(), original)
        memory.save_memory()
        self.assert_defaults(Memory(self.path))
        self.assertEqual(backup.read_bytes(), original)

    def test_backups_have_unique_names_and_do_not_overwrite(self):
        for number in range(3):
            self.path.write_bytes(f"broken-{number}".encode("utf-8"))
            Memory(self.path).save_memory()
        for number, name in enumerate(("memory.corrupt.json", "memory.corrupt.1.json", "memory.corrupt.2.json")):
            self.assertEqual((self.directory / name).read_bytes(), f"broken-{number}".encode("utf-8"))

    def test_backup_failure_stops_recovery_without_changing_original(self):
        self.path.write_bytes(b"broken")
        with patch("memories.os.fsync", side_effect=OSError("Backup failed")):
            with self.assertRaises(OSError):
                Memory(self.path)
        self.assertEqual(self.path.read_bytes(), b"broken")

    def test_invalid_utf8_is_preserved_as_original_bytes(self):
        original = b'\xff\xfe{"partial":'
        self.path.write_bytes(original)
        self.assert_defaults(Memory(self.path))
        self.assertEqual((self.directory / "memory.corrupt.json").read_bytes(), original)

    def test_non_object_json_recovers(self):
        for data in ([], None, "text", 17):
            self.assert_defaults(self.write(data))

    def test_valid_current_save_round_trip(self):
        memory = self.write(self.data)
        memory.save_memory()
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), self.data)
        self.assertEqual(list(self.directory.glob("*.corrupt*.json")), [])

    def test_oldest_supported_format(self):
        data = {name: value for name, value in self.data.items() if name in (
            "questions_asked", "question_history", "repeat_count",
        )}
        memory = self.write(data)
        self.assertEqual(memory.questions_asked, 2)
        self.assertEqual(memory.repeat_count, data["repeat_count"])
        self.assertEqual(memory.achievements, set())
        self.assertEqual(memory.used_personalities, set())

    def test_missing_each_field_preserves_other_data(self):
        for field in self.data:
            with self.subTest(field=field):
                data = self.data.copy()
                del data[field]
                memory = self.write(data)
                self.assertEqual(memory.questions_asked, 2)
                self.assertEqual(memory.question_history, [] if field == "question_history" else self.data["question_history"])
                self.assertEqual(memory.repeat_count, self.data["repeat_count"])
                self.assertEqual(memory.achievements, set() if field == "achievements" else {"First Question"})
                self.assertEqual(memory.used_personalities, set() if field == "used_personalities" else {"sage"})

    def test_empty_object_has_defaults(self):
        self.assert_defaults(self.write({}))

    def test_invalid_question_count_types_use_history_evidence(self):
        for count in ("100", 2.5, True, None, [], {}):
            memory = self.write(dict(self.data, questions_asked=count))
            self.assertEqual(memory.questions_asked, 2)

    def test_negative_question_count_is_rejected(self):
        self.assertEqual(self.write({"questions_asked": -10}).questions_asked, 0)
        self.assertEqual(self.write(dict(self.data, questions_asked=-10)).questions_asked, 2)

    def test_valid_lifetime_count_survives_missing_history(self):
        memory = self.write({"questions_asked": 37})
        self.assertEqual(memory.questions_asked, 37)
        self.assertEqual(memory.question_history, [])
        self.assertEqual(memory.achievements, set())

    def test_invalid_history_type_keeps_other_fields(self):
        for history in (None, "A question?", {}, 42):
            memory = self.write(dict(self.data, question_history=history))
            self.assertEqual(memory.question_history, [])
            self.assertEqual(memory.questions_asked, 2)
            self.assertEqual(memory.repeat_count, self.data["repeat_count"])
            self.assertEqual(memory.achievements, {"First Question"})

    def test_invalid_history_entries_are_filtered_without_reordering(self):
        memory = self.write({"question_history": ["A?", None, 42, {}, "", "  ", "B?", "A?"]})
        self.assertEqual(memory.question_history, ["A?", "B?", "A?"])
        self.assertEqual(memory.questions_asked, 3)
        self.assertEqual(memory.repeat_count, {"a?": 2, "b?": 1})
        self.assertEqual(memory.previous_session_question_count, 3)

    def test_invalid_repeat_count_type_is_rebuilt(self):
        for repeats in (None, [], "bad", 1):
            memory = self.write(dict(self.data, repeat_count=repeats))
            self.assertEqual(memory.repeat_count, self.data["repeat_count"])

    def test_invalid_repeat_values_are_rejected(self):
        repeats = {"negative": -1, "zero": 0, "float": 2.5, "bool": True, "text": "5", "null": None, " ": 5, "valid": 3}
        self.assertEqual(self.write({"repeat_count": repeats}).repeat_count, {"valid": 3})

    def test_repeat_normalization_repairs_stale_counts_without_summing_duplicates(self):
        memory = self.write({
            "question_history": ["A?", " a? ", "A?"],
            "repeat_count": {"A?": 1, " a? ": 2, "older?": 5},
        })
        self.assertEqual(memory.repeat_count, {"a?": 3, "older?": 5})

    def test_invalid_achievement_entries_preserve_valid_names(self):
        memory = self.write(dict(self.data, achievements=["First Question", 3, None, {}, "", " ", "Déjà Vu"]))
        self.assertEqual(memory.achievements, {"First Question", "Déjà Vu"})
        for invalid in (None, "First Question", {}, 42):
            self.assertEqual(self.write(dict(self.data, achievements=invalid)).achievements, set())

    def test_invalid_personalities_are_filtered(self):
        memory = self.write(dict(self.data, used_personalities=["sage", "robot", "wizard", "unknown", 1, None, "SAGE", ""]))
        self.assertEqual(memory.used_personalities, {"sage", "robot", "wizard"})

    def test_partially_valid_save_keeps_valid_progress(self):
        memory = self.write(dict(self.data, questions_asked=37, achievements=42))
        self.assertEqual(memory.questions_asked, 37)
        self.assertEqual(memory.question_history, self.data["question_history"])
        self.assertEqual(memory.repeat_count, self.data["repeat_count"])
        self.assertEqual(memory.used_personalities, {"sage"})
        self.assertEqual(memory.achievements, set())

    def test_unicode_round_trip_is_readable_utf8(self):
        question = "🏆 Déjà Vu — café? 日本語؟"
        memory = Memory(self.path)
        memory.remember_question(question)
        memory.track_repeat(question)
        memory.achievements.add("Déjà Vu")
        memory.save_memory()
        self.assertIn(question, self.path.read_text(encoding="utf-8"))
        restored = Memory(self.path)
        self.assertEqual(restored.question_history, [question])
        self.assertEqual(restored.achievements, {"Déjà Vu"})

    def test_utf8_bom_is_tolerated(self):
        self.path.write_text("\ufeff" + json.dumps(self.data), encoding="utf-8")
        self.assertEqual(Memory(self.path).questions_asked, 2)
        self.assertEqual(list(self.directory.glob("*.corrupt*.json")), [])

    def test_escaped_unpaired_surrogates_are_filtered_before_utf8_save(self):
        data = dict(self.data, question_history=["Good?", "\ud800"],
                    repeat_count={"good?": 1, "\udfff": 2},
                    achievements=["First Question", "\ud800"])
        # JSON permits escaped surrogates, but UTF-8 cannot encode them.
        self.path.write_text(json.dumps(data), encoding="utf-8")
        memory = Memory(self.path)
        self.assertEqual(memory.question_history, ["Good?"])
        self.assertEqual(memory.repeat_count, {"good?": 1})
        self.assertEqual(memory.achievements, {"First Question"})
        memory.save_memory()
        self.assertEqual(Memory(self.path).question_history, ["Good?"])
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_repeat_detection_uses_surviving_counts_when_history_is_missing(self):
        memory = self.write({"questions_asked": 4, "repeat_count": {"An old question?": 4}})
        self.assertTrue(memory.has_asked_before(" AN OLD  QUESTION? "))
        self.assertEqual(memory.track_repeat("An old question?"), 5)
        # Prior-session discovery requires surviving history, not guessed entries.
        self.assertFalse(memory.has_asked_in_previous_session("An old question?"))
        self.assertEqual(memory.question_history, [])

    def test_backups_and_abandoned_temporary_files_are_not_active_saves(self):
        for name in ("memory.corrupt.json", "memory.corrupt.1.json", "memory.json.abandoned.tmp"):
            (self.directory / name).write_text(json.dumps(self.data), encoding="utf-8")
        self.assert_defaults(Memory(self.path))
        self.assertFalse(self.path.exists())

    def test_failed_game_save_retries_without_duplicate_progress_or_rewards(self):
        memory = Memory(self.path)
        real_save = memory.save_memory
        attempts = 0

        def save_with_first_failure():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise OSError("Disk full")
            real_save()

        with patch.object(engine, "Memory", return_value=memory), \
                patch.object(memory, "save_memory", side_effect=save_with_first_failure), \
                patch("builtins.input", side_effect=["1", "A question?", "A question?", "quit"]), \
                patch("achievements.get_current_hour", return_value=12), \
                patch.object(engine, "get_random_event", return_value=None), \
                patch.object(engine, "get_awareness_message", return_value=None), \
                patch.object(engine, "get_response", return_value="NORMAL ANSWER"), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            main.main()
        self.assertEqual(attempts, 2)
        self.assertIn("Could not save memory", output.getvalue())
        self.assertEqual(output.getvalue().count("First Question UNLOCKED!"), 1)
        restored = Memory(self.path)
        self.assertEqual(restored.questions_asked, 2)
        self.assertEqual(restored.question_history, ["A question?"] * 2)
        self.assertEqual(restored.repeat_count, {"a question?": 2})
        self.assertEqual(restored.achievements, {"First Question"})
        self.assertEqual(restored.used_personalities, {"sage"})
        self.assertEqual(memory.previous_session_question_count, 0)
        self.assertEqual(restored.previous_session_question_count, 2)
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_atomic_save_replaces_complete_previous_data(self):
        memory = self.write(self.data)
        original = self.path.read_bytes()
        memory.remember_question("Next?")
        memory.track_repeat("Next?")
        replace = Path.replace
        def verify_replace(temporary, target):
            self.assertEqual(self.path.read_bytes(), original)
            self.assertEqual(temporary.parent, self.path.parent)
            self.assertEqual(json.loads(temporary.read_text(encoding="utf-8"))["questions_asked"], 3)
            return replace(temporary, target)
        with patch.object(Path, "replace", new=verify_replace):
            memory.save_memory()
        self.assertEqual(Memory(self.path).questions_asked, 3)
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_partial_temporary_write_failure_preserves_previous_save(self):
        memory = self.write(self.data)
        original = self.path.read_bytes()
        def fail_write(data, file, **options):
            file.write('{"partial":')
            raise OSError("Disk full")
        with patch("memories.json.dump", side_effect=fail_write), \
                patch.object(Path, "replace") as replace:
            with self.assertRaises(OSError):
                memory.save_memory()
        replace.assert_not_called()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_flush_failure_preserves_previous_save(self):
        memory = self.write(self.data)
        original = self.path.read_bytes()
        with patch("memories.os.fsync", side_effect=OSError("Flush failed")), \
                patch.object(Path, "replace") as replace:
            with self.assertRaises(OSError):
                memory.save_memory()
        replace.assert_not_called()
        self.assertEqual(self.path.read_bytes(), original)

    def test_replace_failure_preserves_previous_save(self):
        memory = self.write(self.data)
        original = self.path.read_bytes()
        with patch.object(Path, "replace", side_effect=PermissionError("File locked")):
            with self.assertRaises(PermissionError):
                memory.save_memory()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_default_save_path_is_beside_module(self):
        # Do not read or write the developer's actual save.
        with patch.object(Memory, "load_memory"):
            memory = Memory()
        self.assertEqual(memory.path, Path(memories.__file__).with_name("memory.json"))

    def test_safety_input_cannot_enter_recovery_backup_or_save(self):
        self.path.write_bytes(b"{damaged")
        sensitive = "I want to hurt myself"
        with patch.object(engine, "Memory", side_effect=lambda: Memory(self.path)), \
                patch("builtins.input", side_effect=["1", sensitive, "A question?", "quit"]), \
                patch("achievements.get_current_hour", return_value=12), \
                patch.object(engine, "get_random_event", return_value=None), \
                patch.object(engine, "get_awareness_message", return_value=None), \
                patch.object(engine, "get_response", return_value="NORMAL ANSWER"), \
                contextlib.redirect_stdout(io.StringIO()):
            main.main()
        self.assertEqual((self.directory / "memory.corrupt.json").read_bytes(), b"{damaged")
        for file in self.directory.iterdir():
            self.assertNotIn(sensitive.encode("utf-8"), file.read_bytes())
        restored = Memory(self.path)
        self.assertEqual(restored.questions_asked, 1)
        self.assertEqual(restored.question_history, ["A question?"])
        self.assertEqual(restored.repeat_count, {"a question?": 1})


if __name__ == "__main__":
    unittest.main()
