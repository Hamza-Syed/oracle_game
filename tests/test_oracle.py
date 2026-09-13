import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from achievements import AchievementTracker
import main
import game as engine
from memories import Memory
from personalities import RESPONSES, get_response, get_topic_reaction
from self_awareness import get_awareness_message


class OracleTests(unittest.TestCase):
    def setUp(self):
        clock = patch("achievements.get_current_hour", return_value=12)
        clock.start()
        self.addCleanup(clock.stop)
        awareness = patch("game.get_awareness_message", return_value=None)
        awareness.start()
        self.addCleanup(awareness.stop)
        events = patch("game.get_random_event", return_value=None)
        events.start()
        self.addCleanup(events.stop)
        choices = patch("personalities.random.choice", side_effect=lambda pool: pool[0])
        choices.start()
        self.addCleanup(choices.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "memory.json"

    def run_game(self, inputs):
        output = io.StringIO()
        with patch.object(engine, "Memory", side_effect=lambda: Memory(self.path)), \
                patch("builtins.input", side_effect=inputs), \
                contextlib.redirect_stdout(output):
            main.main()
        return output.getvalue()

    def test_game_commands_switching_and_restart(self):
        output = self.run_game([
            "banana", "1", "", "Will I pass my exam?", "change", "99", "3",
            " WILL I PASS MY EXAM? ", "stats", "history", "achievements", "quit",
        ])
        self.assertEqual(output.count("Invalid selection"), 2)
        self.assertIn("The Oracle senses academic uncertainty.", output)
        self.assertIn("The seas of knowledge be rough today.", output)
        self.assertIn("You seem concerned about this.", output)
        self.assertEqual(Memory(self.path).questions_asked, 2)
        output = self.run_game(["2", "Will I pass my exam?", "quit"])
        self.assertIn("remembers 2 previous questions", output)
        self.assertIn("The answer may not change", output)
        self.assertNotIn("First Question UNLOCKED!", output)
        self.assertEqual(Memory(self.path).questions_asked, 3)

    def test_all_achievements_persist_and_unlock_once(self):
        memory = Memory(self.path)
        tracker = AchievementTracker()
        unlocked = []
        expected_unlocks = {
            1: ["First Question"],
            5: ["The Doubter"],
            10: ["Persistent Seeker", "Indecisive"],
            100: ["Oracle Addict"],
        }
        for count in range(1, 101):
            memory.remember_question("Will I get a job?")
            repeat = memory.track_repeat("Will I get a job?")
            new_achievements = tracker.check_achievements(memory, repeat)
            self.assertEqual(new_achievements, expected_unlocks.get(count, []))
            unlocked.extend(new_achievements)
        self.assertEqual(unlocked, [
            "First Question", "The Doubter", "Persistent Seeker", "Indecisive", "Oracle Addict",
        ])
        memory.save_memory()
        restored = Memory(self.path)
        self.assertEqual(restored.questions_asked, 100)
        self.assertEqual(restored.repeat_count["will i get a job?"], 100)
        self.assertEqual(tracker.check_achievements(restored, 100), [])

    def test_older_save_unlocks_and_persists_achievements(self):
        self.path.write_text(json.dumps({
            "questions_asked": 9,
            "question_history": ["Will I get a job?"] * 9,
            "repeat_count": {"will i get a job?": 9},
        }), encoding="utf-8")
        output = self.run_game(["1", "Will I pass my exam?", "quit"])
        expected = {"First Question", "Persistent Seeker", "The Doubter"}
        for name in expected:
            self.assertIn(f"🏆 {name} UNLOCKED!", output)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(set(saved["achievements"]), expected)
        self.assertEqual(saved["questions_asked"], 10)
        output = self.run_game(["3", "Will I get an internship?", "quit"])
        self.assertNotIn("UNLOCKED!", output)
        self.assertEqual(Memory(self.path).achievements, expected)

    def test_repeat_achievement_spans_sessions(self):
        self.run_game(["1"] + ["Will I get a job?"] * 4 + ["quit"])
        self.assertNotIn("The Doubter", Memory(self.path).achievements)
        output = self.run_game(["2", " WILL I GET A JOB? ", "quit"])
        self.assertIn("🏆 The Doubter UNLOCKED!", output)
        output = self.run_game(["3", "Will I get a job?", "quit"])
        self.assertNotIn("UNLOCKED!", output)

    def test_legacy_save_repairs_counts_and_normalizes_repeats(self):
        self.path.write_text(json.dumps({
            "questions_asked": 2,
            "question_history": ["Hello?", " HELLO? "],
            "repeat_count": {"hello?": 1},
        }), encoding="utf-8")
        memory = Memory(self.path)
        self.assertTrue(memory.has_asked_before("hello?"))
        self.assertEqual(memory.repeat_count, {"hello?": 2})
        self.assertEqual(memory.achievements, set())

    def test_invalid_save_is_preserved(self):
        for contents in ("{broken", '{"question_history": 42}'):
            self.path.write_text(contents, encoding="utf-8")
            output = self.run_game(["quit"])
            self.assertNotIn("Could not load memory", output)
            self.assertIn("remembers 0 previous questions", output)
            self.assertEqual(self.path.read_text(encoding="utf-8"), contents)
            if contents == "{broken":
                self.assertEqual(self.path.with_name("memory.corrupt.json").read_text(encoding="utf-8"), contents)

    def test_topics_and_personality_responses(self):
        memory = Memory(self.path)
        self.assertEqual(memory.detect_topic("INTERNSHIPS?"), "internship")
        self.assertEqual(memory.detect_topic("An example of joy?"), "other")
        self.assertEqual(memory.get_favorite_topic(), "unknown")
        memory.remember_question("Will I get a job?")
        self.assertEqual(memory.get_favorite_topic(), "job")
        for personality, responses in RESPONSES.items():
            self.assertIn(get_response(personality), responses)
            for topic in ("exam", "job", "internship"):
                self.assertTrue(get_topic_reaction(personality, topic))
            self.assertIsNone(get_topic_reaction(personality, "other"))

    def test_awareness_milestones(self):
        for count, message in (
            (25, "You've been asking many questions lately."),
            (100, "I wonder why humans seek certainty."),
            (250, "consider one of mine"),
        ):
            memory = Memory(self.path)
            memory.question_history = ["A question?"] * (count - 1)
            memory.save_memory()
            # Milestone dialogue is now occasional; force a successful roll.
            with patch("game.get_awareness_message", side_effect=lambda personality, count:
                       get_awareness_message(personality, count, roll=0)), \
                    patch("self_awareness.random.choice", side_effect=lambda pool: pool[0]):
                output = self.run_game(["1", "Another question?", "quit"])
            self.assertIn(message, output)

    def test_full_pipeline_saves_post_question_state_once_before_entertainment(self):
        memory = Memory(self.path)
        tracker = AchievementTracker()

        def verify_saved_state(question, personality):
            restored = Memory(self.path)
            self.assertEqual(restored.questions_asked, 1)
            self.assertEqual(restored.question_history, [question])
            self.assertEqual(restored.repeat_count, {question.casefold(): 1})
            self.assertEqual(restored.achievements, {"First Question"})
            self.assertEqual(restored.used_personalities, {personality})
            return None

        with patch.object(engine, "Memory", return_value=memory), \
                patch.object(engine, "AchievementTracker", return_value=tracker), \
                patch.object(memory, "remember_question", wraps=memory.remember_question) as remember, \
                patch.object(memory, "track_repeat", wraps=memory.track_repeat) as repeat, \
                patch.object(memory, "save_memory", wraps=memory.save_memory) as save, \
                patch.object(tracker, "check_achievements", wraps=tracker.check_achievements) as unlock, \
                patch.object(engine, "get_easter_egg_response", side_effect=verify_saved_state) as egg, \
                patch.object(engine, "get_response", return_value="NORMAL ANSWER") as answer, \
                patch("builtins.input", side_effect=["1", "Will I pass my exam?", "quit"]), \
                contextlib.redirect_stdout(io.StringIO()):
            main.main()
        for mocked in (remember, repeat, save, unlock, egg, answer):
            self.assertEqual(mocked.call_count, 1)

    def test_history_wording_and_repeat_normalization_across_restart(self):
        question = "Will  STRASSE\tbe sunny?"
        self.run_game(["1", question, "quit"])
        restored = Memory(self.path)
        self.assertEqual(restored.question_history, [question])
        self.assertTrue(restored.has_asked_before(" will straße be SUNNY? "))
        self.assertTrue(restored.has_asked_in_previous_session(" will straße be SUNNY? "))
        # Repeat matching retains punctuation and word order, unlike egg matching.
        for different in ("Will strasse be sunny!", "Will sunny be strasse?"):
            self.assertFalse(restored.has_asked_before(different))
            self.assertFalse(restored.has_asked_in_previous_session(different))
        output = self.run_game(["1", "will straße be SUNNY?", "quit"])
        self.assertIn("Déjà Vu UNLOCKED!", output)
        self.assertEqual(Memory(self.path).repeat_count, {"will strasse be sunny?": 2})


if __name__ == "__main__":
    unittest.main()
