import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from achievements import AchievementTracker
from commands import (
    COMMAND_HELP, handle_display_command, show_achievements,
    show_help, show_history, show_stats,
)
import main
import game as engine
from memories import Memory


class CommandTests(unittest.TestCase):
    def setUp(self):
        clock = patch("achievements.get_current_hour", return_value=12)
        clock.start()
        self.addCleanup(clock.stop)
        events = patch("game.get_random_event", return_value=None)
        events.start()
        self.addCleanup(events.stop)
        choices = patch("personalities.random.choice", side_effect=lambda pool: pool[0])
        choices.start()
        self.addCleanup(choices.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "memory.json"
        self.memory = Memory(self.path)
        self.tracker = AchievementTracker()

    def capture(self, function, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            function(*args)
        return output.getvalue()

    def ask(self, question):
        self.memory.remember_question(question)
        self.memory.track_repeat(question)

    def test_each_display_command_leaves_memory_and_save_unchanged(self):
        self.ask("Will I pass my exam?")
        self.memory.save_memory()
        original_state = copy.deepcopy(vars(self.memory))
        original_save = self.path.read_bytes()
        for command in ("help", "stats", "history", "achievements"):
            with self.subTest(command=command):
                with contextlib.redirect_stdout(io.StringIO()):
                    handled = handle_display_command(
                        f"  {command.upper()}  ", self.memory, "sage", self.tracker,
                    )
                self.assertTrue(handled)
                self.assertEqual(vars(self.memory), original_state)
                self.assertEqual(self.path.read_bytes(), original_save)

    def test_commands_bypass_question_processing(self):
        with patch.object(engine, "Memory", return_value=self.memory), \
                patch("builtins.input", side_effect=[
                    "1", " HELP ", " STATS ", " HISTORY ", " ACHIEVEMENTS ", " QUIT ",
                ]), \
                patch.object(engine, "get_response") as answer, \
                patch.object(engine, "get_topic_reaction") as reaction, \
                patch.object(Memory, "detect_topic") as topic, \
                patch.object(AchievementTracker, "check_achievements") as unlock:
            output = self.capture(main.main)
        answer.assert_not_called()
        reaction.assert_not_called()
        topic.assert_not_called()
        unlock.assert_not_called()
        self.assertEqual(self.memory.questions_asked, 0)
        self.assertEqual(self.memory.question_history, [])
        self.assertEqual(self.memory.repeat_count, {})
        self.assertEqual(self.memory.achievements, set())
        self.assertIn("Farewell, seeker.", output)

    def test_help_explains_all_commands(self):
        output = self.capture(show_help)
        for command, explanation in COMMAND_HELP.items():
            self.assertIn(f"{command}: {explanation}", output)

    def test_blank_and_whitespace_input_leave_progress_untouched(self):
        original = copy.deepcopy(vars(self.memory))
        with patch.object(engine, "Memory", return_value=self.memory), \
                patch("builtins.input", side_effect=["1", "", " \t ", "quit"]), \
                patch.object(engine, "assess_safety") as safety, \
                patch.object(engine, "get_random_event") as events, \
                patch.object(engine, "get_awareness_message") as awareness, \
                patch.object(engine, "get_response") as answer, \
                patch.object(AchievementTracker, "check_achievements") as unlock:
            output = self.capture(main.main)
        for mocked in (safety, events, awareness, answer, unlock):
            mocked.assert_not_called()
        self.assertEqual(vars(self.memory), original)
        self.assertFalse(self.path.exists())
        self.assertEqual(output.count("Ask a question first, seeker."), 2)

    def test_mixed_case_commands_and_same_personality_switch_are_neutral(self):
        self.ask("A question?")
        self.memory.save_memory()
        original = copy.deepcopy(vars(self.memory))
        saved = self.path.read_bytes()
        with patch.object(engine, "Memory", return_value=self.memory), \
                patch("builtins.input", side_effect=[
                    "1", " HeLp ", " StAtS ", " HiStOrY ", " AcHiEvEmEnTs ",
                    *[item for _ in range(6) for item in (" ChAnGe ", "1")], " QuIt ",
                ]), \
                patch.object(engine, "assess_safety") as safety, \
                patch.object(engine, "get_random_event") as events, \
                patch.object(engine, "get_awareness_message") as awareness, \
                patch.object(engine, "get_response") as answer:
            output = self.capture(main.main)
        for mocked in (safety, events, awareness, answer):
            mocked.assert_not_called()
        self.assertEqual(vars(self.memory), original)
        self.assertEqual(self.path.read_bytes(), saved)
        self.assertNotIn("UNLOCKED!", output)

    def test_command_words_inside_questions_are_normal_gameplay(self):
        questions = ["Will you help me?", "Should I change my plans?", "Should I quit my job?"]
        with patch.object(engine, "Memory", return_value=self.memory), \
                patch("builtins.input", side_effect=["1", *questions, "quit"]), \
                patch.object(engine, "get_response", return_value="NORMAL ANSWER") as answer:
            self.capture(main.main)
        self.assertEqual(answer.call_count, 3)
        self.assertEqual(self.memory.question_history, questions)
        self.assertEqual(self.memory.questions_asked, 3)

    def test_stats_uses_persistent_memory(self):
        for question in ("Will I pass my exam?", " WILL I PASS MY EXAM? ", "A job?"):
            self.ask(question)
        self.memory.achievements.add("First Question")
        self.memory.save_memory()
        output = self.capture(show_stats, Memory(self.path), "student", self.tracker)
        for expected in (
            "Total lifetime questions asked: 3", "Unique questions asked: 2",
            "Repeated questions (after the first asking): 1",
            "Current personality: Sarcastic Student", "Achievements unlocked: 1",
            "Known non-secret achievements: 4",
        ):
            self.assertIn(expected, output)

    def test_history_only_shows_latest_ten_real_questions(self):
        for number in range(1, 13):
            self.ask(f"Question {number}?")
        # Simulate commands accidentally stored by an older game version.
        self.memory.question_history.extend(f" {name.upper()} " for name in COMMAND_HELP)
        original_history = self.memory.question_history.copy()
        output = self.capture(show_history, self.memory)
        lines = output.strip().splitlines()
        self.assertIn("oldest to newest", lines[0])
        self.assertEqual(lines[1:], [f"{n}. Question {n}?" for n in range(3, 13)])
        self.assertEqual(self.memory.question_history, original_history)

    def test_empty_history_is_friendly(self):
        output = self.capture(show_history, self.memory)
        self.assertIn("You haven't asked any questions yet", output)

    def test_achievement_display_distinguishes_locked_and_unlocked(self):
        self.memory.achievements.add("First Question")
        output = self.capture(show_achievements, self.memory, self.tracker)
        self.assertIn("[Unlocked] First Question:", output)
        for name in ("Persistent Seeker", "The Doubter", "Oracle Addict"):
            self.assertIn(f"[Locked] {name}:", output)

    def test_future_secrets_stay_hidden_until_unlocked(self):
        self.tracker.descriptions = dict(self.tracker.descriptions, Secret="A hidden reward.")
        self.tracker.secret_achievements = self.tracker.secret_achievements | {"Secret"}
        output = self.capture(show_achievements, self.memory, self.tracker)
        self.assertNotIn("Secret", output)
        self.assertNotIn("A hidden reward", output)
        self.assertEqual(self.tracker.get_normal_achievement_count(), 4)
        self.memory.achievements.add("Secret")
        output = self.capture(show_achievements, self.memory, self.tracker)
        self.assertIn("[Unlocked] Secret: A hidden reward.", output)

    def test_unrecognized_command_is_left_for_question_processing(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            handled = handle_display_command(
                "Will you help me?", self.memory, "pirate", self.tracker,
            )
        self.assertFalse(handled)
        self.assertEqual(output.getvalue(), "")

    def test_change_and_quit_preserve_actual_questions(self):
        with patch.object(engine, "Memory", return_value=self.memory), \
                patch("builtins.input", side_effect=[
                    "1", "Will I pass my exam?", " CHANGE ", "3", " STATS ",
                    "Will I get a job?", " HISTORY ", " QUIT ",
                ]):
            output = self.capture(main.main)
        self.assertIn("Current personality: Pirate", output)
        self.assertIn("Ye seek employment aboard destiny's ship.", output)
        self.assertIn("Farewell, seeker.", output)
        self.assertEqual(self.memory.question_history, [
            "Will I pass my exam?", "Will I get a job?",
        ])
        self.assertEqual(self.memory.questions_asked, 2)
        self.assertEqual(len(self.memory.repeat_count), 2)


if __name__ == "__main__":
    unittest.main()
