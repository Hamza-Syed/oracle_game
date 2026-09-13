"""Exercise the shared engine directly, without terminal input or text parsing."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import game as engine
from game import OracleGame
from memories import Memory
from personalities import PERSONALITY_NAMES
from random_events import get_random_event
from self_awareness import get_awareness_message


class GameTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "memory.json"
        self.memory = Memory(self.path)
        self.game = OracleGame(self.memory)
        # Any terminal I/O, including indirectly from command helpers, is a failure.
        for target, options in (
            ("builtins.input", {"side_effect": AssertionError("Engine requested terminal input")}),
            ("builtins.print", {"side_effect": AssertionError("Engine printed terminal output")}),
            ("achievements.get_current_hour", {"return_value": 12}),
            ("game.get_random_event", {"return_value": None}),
            ("game.get_awareness_message", {"return_value": None}),
            ("game.get_response", {"return_value": "NORMAL ANSWER"}),
        ):
            mock = patch(target, **options)
            mock.start()
            self.addCleanup(mock.stop)

    def select(self):
        self.game.select_personality("sage")

    def roles(self, result):
        return [message.role for message in result.messages]

    def test_normal_question_returns_messages_and_counts_once(self):
        self.select()
        result = self.game.process_input("  Will I pass my exam?  ")
        self.assertEqual(result.kind, "question")
        self.assertEqual(self.roles(result), ["topic", "achievement", "answer"])
        self.assertEqual(result.messages[-1].text, "NORMAL ANSWER")
        self.assertEqual(result.new_achievements, ["First Question"])
        self.assertIsNone(result.save_error)
        self.assertEqual(self.memory.questions_asked, 1)
        self.assertEqual(self.memory.repeat_count, {"will i pass my exam?": 1})
        self.assertEqual(self.memory.question_history, ["Will I pass my exam?"])

    def test_blank_and_whitespace_do_not_progress(self):
        self.select()
        original = copy.deepcopy(vars(self.memory))
        with patch.object(engine, "assess_safety") as safety:
            for text in ("", "  \t\n"):
                self.assertEqual(self.game.process_input(text).kind, "blank")
        safety.assert_not_called()
        self.assertEqual(vars(self.memory), original)
        self.assertFalse(self.path.exists())

    def test_each_command_returns_structured_data_without_progress(self):
        self.select()
        original = copy.deepcopy(vars(self.memory))
        expected = {
            "help": self.game.get_help(), "stats": self.game.get_stats(),
            "history": self.game.get_history(), "achievements": self.game.get_achievements(),
        }
        with patch.object(engine, "assess_safety") as safety, \
                patch.object(engine, "get_random_event") as event, \
                patch.object(engine, "get_awareness_message") as awareness:
            for command, data in expected.items():
                result = self.game.process_input(f"  {command.upper()}  ")
                self.assertEqual(result.kind, command)
                self.assertEqual(result.data, data)
                self.assertEqual(result.new_achievements, [])
            self.assertEqual(self.game.process_input(" ChAnGe ").kind, "select_personality")
            self.assertEqual(self.game.process_input(" QuIt ").kind, "quit")
        for mocked in (safety, event, awareness):
            mocked.assert_not_called()
        self.assertEqual(vars(self.memory), original)
        self.assertFalse(self.path.exists())

    def test_all_personality_ids_and_names_are_exposed_as_a_copy(self):
        choices = self.game.get_personalities()
        self.assertEqual(choices, PERSONALITY_NAMES)
        self.assertEqual(len(choices), 7)
        choices.clear()
        self.assertEqual(len(self.game.get_personalities()), 7)
        for key, name in PERSONALITY_NAMES.items():
            result = self.game.select_personality(key)
            self.assertEqual(result.kind, "personality_selected")
            self.assertEqual(self.game.get_stats()["personality_id"], key)
            self.assertEqual(self.game.get_stats()["personality_name"], name)

    def test_initial_same_and_invalid_selection_do_not_count_switches(self):
        self.select()
        original = copy.deepcopy(vars(self.memory))
        for _ in range(6):
            self.assertEqual(self.game.select_personality("sage").new_achievements, [])
        for invalid in ("missing", "SAGE", None, [], 1):
            self.assertEqual(self.game.select_personality(invalid).kind, "invalid_selection")
        self.assertEqual(self.game.personality, "sage")
        self.assertEqual(self.game.achievement_tracker.personality_changes, 0)
        self.assertEqual(vars(self.memory), original)
        self.assertFalse(self.path.exists())

    def test_real_switches_unlock_once_save_and_do_not_mark_personalities_used(self):
        self.select()
        for number, key in enumerate(["student", "pirate", "wizard", "alien", "robot", "sage"], 1):
            result = self.game.select_personality(key)
            self.assertEqual(result.new_achievements, ["Personality Crisis"] if number == 5 else [])
        self.assertEqual(Memory(self.path).achievements, {"Personality Crisis"})
        self.assertEqual(self.memory.used_personalities, set())
        self.assertEqual(self.memory.questions_asked, 0)

    def test_question_before_selection_requests_selection_without_progress(self):
        self.assertEqual(self.game.process_input("A question?").kind, "select_personality")
        self.assertEqual(self.memory.questions_asked, 0)
        self.assertFalse(self.path.exists())

    def test_safety_result_short_circuits_all_gameplay_and_contains_no_input(self):
        self.select()
        self.game.process_input("A question?")
        state = copy.deepcopy(vars(self.memory))
        saved = self.path.read_bytes()
        sensitive = "I want to hurt myself"
        with patch.object(engine, "get_easter_egg_response") as egg, \
                patch.object(engine, "get_random_event") as event, \
                patch.object(engine, "get_awareness_message") as awareness, \
                patch.object(engine, "get_response") as answer, \
                patch.object(self.memory, "save_memory") as save:
            result = self.game.process_input(sensitive)
        for mocked in (egg, event, awareness, answer, save):
            mocked.assert_not_called()
        self.assertEqual(result.kind, "safety")
        self.assertEqual(self.roles(result), ["safety"])
        self.assertEqual(result.new_achievements, [])
        self.assertNotIn(sensitive, repr(result))
        self.assertEqual(vars(self.memory), state)
        self.assertEqual(self.path.read_bytes(), saved)

    def test_safety_also_works_before_personality_selection(self):
        result = self.game.process_input("I want to hurt myself")
        self.assertEqual(result.kind, "safety")
        self.assertFalse(self.path.exists())

    def test_easter_egg_returns_special_result_and_suppresses_other_replies(self):
        self.select()
        with patch.object(engine, "get_random_event") as event, \
                patch.object(engine, "get_awareness_message") as awareness, \
                patch.object(engine, "get_response") as answer:
            result = self.game.process_input("Are you real?")
        self.assertEqual(result.kind, "easter_egg")
        self.assertEqual(self.roles(result), ["achievement", "easter_egg"])
        for mocked in (event, awareness, answer):
            mocked.assert_not_called()
        self.assertEqual(Memory(self.path).questions_asked, 1)

    def force_event(self, roll):
        with patch("random_events.random.choice", side_effect=lambda pool: pool[0]):
            event = get_random_event("sage", roll=roll)
        with patch.object(engine, "get_random_event", return_value=event):
            return self.game.process_input("A question?")

    def test_accompanying_event_keeps_normal_answer(self):
        self.select()
        result = self.force_event(0.95)
        self.assertEqual(result.kind, "event")
        self.assertEqual(result.data["rarity"], "uncommon")
        self.assertEqual(self.roles(result), ["achievement", "event", "answer"])

    def test_replacement_event_skips_normal_answer(self):
        self.select()
        with patch.object(engine, "get_response") as answer:
            result = self.force_event(0.99)
        answer.assert_not_called()
        self.assertEqual(result.kind, "event")
        self.assertEqual(self.roles(result), ["achievement", "event"])
        self.assertFalse(result.data["show_normal_answer"])

    def test_forced_awareness_is_an_ordered_message(self):
        self.select()
        self.memory.questions_asked = 24
        with patch.object(engine, "get_awareness_message", side_effect=lambda personality, count:
                          get_awareness_message(personality, count, roll=0)), \
                patch("self_awareness.random.choice", side_effect=lambda pool: pool[0]):
            result = self.game.process_input("A question?")
        self.assertEqual(self.roles(result)[-2:], ["awareness", "answer"])
        self.assertEqual(self.memory.questions_asked, 25)

    def test_extremely_rare_event_does_not_call_awareness(self):
        self.select()
        self.memory.questions_asked = 500
        with patch.object(engine, "get_awareness_message") as awareness:
            result = self.force_event(0.999)
        awareness.assert_not_called()
        self.assertEqual(result.data["rarity"], "extremely_rare")
        self.assertNotIn("awareness", self.roles(result))
        self.assertNotIn("answer", self.roles(result))

    def test_persistence_and_prior_session_achievements_through_engine(self):
        self.select()
        first = self.game.process_input("A question?")
        self.assertEqual(first.new_achievements, ["First Question"])
        same_session = self.game.process_input("A QUESTION?")
        self.assertEqual(same_session.new_achievements, [])
        restored = OracleGame(Memory(self.path))
        self.assertEqual(restored.memory.questions_asked, 2)
        self.assertEqual(restored.memory.used_personalities, {"sage"})
        restored.select_personality("pirate")
        result = restored.process_input("a question?")
        self.assertEqual(result.new_achievements, ["Déjà Vu"])
        self.assertEqual(restored.memory.repeat_count, {"a question?": 3})
        self.assertEqual(restored.process_input("a question?").new_achievements, [])

    def test_stats_history_achievements_access_needs_no_command_strings(self):
        self.select()
        for number in range(12):
            self.game.process_input(f"Question {number}?")
        saved = self.path.read_bytes()
        stats = self.game.get_stats()
        history = self.game.get_history()
        achievements = self.game.get_achievements()
        self.assertEqual(stats["questions_asked"], 12)
        self.assertEqual(stats["unique_questions"], 12)
        self.assertEqual(stats["repeated_questions"], 0)
        self.assertEqual(len(history), 10)
        self.assertEqual(history[0], {"number": 3, "question": "Question 2?"})
        by_name = {entry["name"]: entry for entry in achievements}
        self.assertTrue(by_name["First Question"]["unlocked"])
        self.assertFalse(by_name["Oracle Addict"]["unlocked"])
        for entry in achievements:
            if entry["name"] is None:
                self.assertIsNone(entry["description"])
        self.assertNotIn("Night Owl", by_name)
        # Returned snapshots do not expose mutable backing collections.
        stats.clear()
        history[0]["question"] = "edited"
        achievements.clear()
        self.assertEqual(self.game.get_history()[0]["question"], "Question 2?")
        self.assertTrue(self.game.get_achievements())
        self.assertEqual(self.path.read_bytes(), saved)

    def test_save_error_is_structured_and_next_question_retries(self):
        self.select()
        with patch.object(self.memory, "save_memory", side_effect=OSError("Disk full")):
            result = self.game.process_input("A question?")
        self.assertEqual(result.save_error, "Disk full")
        self.assertEqual(result.kind, "question")
        self.assertEqual(result.new_achievements, ["First Question"])
        self.assertEqual(self.roles(result)[:2], ["error", "error"])
        self.assertEqual(self.roles(result)[-1], "answer")
        result = self.game.process_input("A question?")
        self.assertIsNone(result.save_error)
        self.assertEqual(result.new_achievements, [])
        self.assertEqual(Memory(self.path).questions_asked, 2)

    def test_time_hook_still_controls_achievement_results(self):
        self.select()
        with patch("achievements.get_current_hour", return_value=0):
            result = self.game.process_input("A question?")
        self.assertIn("Night Owl", result.new_achievements)


if __name__ == "__main__":
    unittest.main()
