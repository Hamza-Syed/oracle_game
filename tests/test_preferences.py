import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import game as engine
import main
from game import OracleGame
from memories import Memory
from personalities import (PERSONALITY_NAMES, PREFERENCE_REPLIES,
                           get_preference_subject, get_preference_response)


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "memory.json"
        self.game = OracleGame(Memory(self.path))
        self.game.select_personality("sage")
        for target, options in (
            ("achievements.get_current_hour", {"return_value": 12}),
            ("personalities.random.choice", {"side_effect": lambda pool: pool[0]}),
        ):
            mocked = patch(target, **options)
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_subject_extraction_preserves_case_and_internal_punctuation(self):
        for question, subject in (
            ("Do you like chicken?", "chicken"), ("DO YOU LIKE WATER", "WATER"),
            (" do you like pizza?! ", "pizza"), ("Do  you\tlike  Cats & Dogs?", "Cats & Dogs"),
            ("Do you like sci-fi?", "sci-fi"), ("Do you like {computers}?", "{computers}"),
        ):
            self.assertEqual(get_preference_subject(question), subject)
            self.assertIn(subject, get_preference_response(question, "sage"))

    def test_real_preference_questions_count_once_and_skip_entertainment(self):
        questions = ["Do you like chicken?", "Do you like water?", "DO YOU LIKE PIZZA?!", "Do you like cats?"]
        with patch.object(engine, "get_response") as answer, \
                patch.object(engine, "get_random_event") as event, \
                patch.object(engine, "get_awareness_message") as awareness, \
                patch.object(engine, "get_topic_reaction") as topic:
            for count, question in enumerate(questions, 1):
                result = self.game.process_input(question)
                self.assertEqual(result.kind, "preference")
                self.assertEqual(result.messages[-1].role, "answer")
                self.assertEqual(self.game.memory.questions_asked, count)
            for mocked in (answer, event, awareness, topic):
                mocked.assert_not_called()
        restored = Memory(self.path)
        self.assertEqual(restored.question_history, questions)
        self.assertEqual(restored.used_personalities, {"sage"})
        self.assertEqual(restored.repeat_count[questions[0].casefold()], 1)

    def test_repeated_preferences_persist_and_unlock_existing_achievements(self):
        first = self.game.process_input("Do you like chicken?")
        self.assertIn("First Question", first.new_achievements)
        self.assertNotIn("Déjà Vu", self.game.process_input("Do you like chicken?").new_achievements)
        self.assertEqual(self.game.memory.repeat_count, {"do you like chicken?": 2})
        restored = OracleGame(Memory(self.path))
        restored.select_personality("pirate")
        result = restored.process_input("DO YOU LIKE CHICKEN?")
        self.assertIn("Déjà Vu", result.new_achievements)
        for _ in range(7):
            result = restored.process_input("Do you like chicken?")
        self.assertIn("Persistent Seeker", result.new_achievements)
        self.assertIn("The Doubter", restored.memory.achievements)
        self.assertEqual(restored.memory.questions_asked, 10)
        self.assertEqual(restored.memory.used_personalities, {"sage", "pirate"})
        self.assertEqual(set(json.loads(self.path.read_text(encoding="utf-8"))), {
            "questions_asked", "question_history", "repeat_count", "achievements", "used_personalities",
        })

    def test_all_personalities_have_multiple_distinct_selectable_templates(self):
        self.assertEqual(set(PREFERENCE_REPLIES), set(PERSONALITY_NAMES))
        first_replies = set()
        for personality, templates in PREFERENCE_REPLIES.items():
            self.assertGreaterEqual(len(set(templates)), 2)
            for template in templates:
                with patch("personalities.random.choice", return_value=template) as choose:
                    reply = get_preference_response("Do you like computers?", personality)
                self.assertEqual(reply, template.format(subject="computers"))
                choose.assert_called_once_with(templates)
            first_replies.add(get_preference_response("Do you like computers?", personality))
        self.assertEqual(len(first_replies), 7)

    def test_nonmatching_forms_and_long_acknowledgments_remain_questions(self):
        questions = ["Why do you like chicken?", "Do you know if I like chicken?", "Do you like?",
                     "Will you like water someday?", "Does she like chicken?", "Do you like ...?!",
                     "Will it be wonderful?", "Perfect, will I win?", "Is it lovely?", "Is this excellent?"]
        with patch.object(engine, "get_random_event", return_value=None), \
                patch.object(engine, "get_awareness_message", return_value=None), \
                patch.object(engine, "get_response", return_value="Normal answer"):
            for question in questions:
                self.assertIsNone(get_preference_subject(question))
                self.assertEqual(self.game.process_input(question).kind, "question")

    def test_safety_precedes_preference_detection(self):
        with patch.object(engine, "get_preference_response") as banter:
            self.assertEqual(self.game.process_input("Do you like water? I want to hurt myself").kind, "safety")
            banter.assert_not_called()
        with patch.object(engine, "assess_safety", return_value={"risk": "ambiguous", "immediate": False}), \
                patch.object(engine, "get_preference_response") as banter:
            self.assertEqual(self.game.process_input("Do you like chicken?").kind, "safety")
            banter.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_easter_egg_wins_over_future_overlapping_preference_phrase(self):
        with patch.object(engine, "get_easter_egg_response", return_value="Discovery"), \
                patch.object(engine, "get_preference_response") as banter:
            result = self.game.process_input("Do you like chicken?")
        self.assertEqual(result.kind, "easter_egg")
        banter.assert_not_called()

    def test_terminal_displays_banter_and_history_keeps_original_wording(self):
        question = "Do  you like Chicken?!"
        with patch.object(engine, "Memory", return_value=self.game.memory), \
                patch("builtins.input", side_effect=["1", question, "quit"]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            main.main()
        self.assertIn(get_preference_response(question, "sage"), output.getvalue())
        self.assertEqual(Memory(self.path).question_history, [question])


if __name__ == "__main__":
    unittest.main()
