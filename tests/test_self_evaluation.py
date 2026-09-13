import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import game as engine
from game import OracleGame
from memories import Memory
from personalities import (PERSONALITY_NAMES, SELF_EVALUATION_PHRASES,
                           SELF_EVALUATION_REPLIES, get_self_evaluation_response)


class SelfEvaluationTests(unittest.TestCase):
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
            mock = patch(target, **options)
            mock.start()
            self.addCleanup(mock.stop)

    def test_all_supported_phrases_are_counted_once_and_skip_random_entertainment(self):
        count = 0
        with patch.object(engine, "get_response") as answer, \
                patch.object(engine, "get_random_event") as event, \
                patch.object(engine, "get_awareness_message") as awareness:
            for phrases in SELF_EVALUATION_PHRASES.values():
                for phrase in phrases:
                    question = phrase.upper() + "?!"
                    result = self.game.process_input("  " + question + "  ")
                    count += 1
                    self.assertEqual(result.kind, "self_evaluation")
                    self.assertEqual(self.game.memory.questions_asked, count)
                    self.assertEqual(self.game.memory.question_history[-1], question)
                    self.assertEqual(self.game.memory.repeat_count[question.casefold()], 1)
                    self.assertEqual(result.messages[-1].role, "answer")
            for mocked in (answer, event, awareness):
                mocked.assert_not_called()
        self.assertEqual(self.game.memory.used_personalities, {"sage"})
        self.assertEqual(Memory(self.path).questions_asked, count)

    def test_repeats_prior_sessions_and_achievements_persist_without_extra_labels(self):
        result = self.game.process_input("Am I smart?")
        self.assertIn("First Question", result.new_achievements)
        result = self.game.process_input("Am I smart?")
        self.assertNotIn("Déjà Vu", result.new_achievements)
        restored = OracleGame(Memory(self.path))
        restored.select_personality("pirate")
        result = restored.process_input("AM I SMART?")
        self.assertIn("Déjà Vu", result.new_achievements)
        self.assertEqual(restored.memory.repeat_count, {"am i smart?": 3})
        self.assertEqual(restored.memory.used_personalities, {"sage", "pirate"})
        for _ in range(7):
            result = restored.process_input("Am I smart?")
        self.assertIn("Persistent Seeker", result.new_achievements)
        self.assertIn("The Doubter", restored.memory.achievements)
        self.assertEqual(set(json.loads(self.path.read_text(encoding="utf-8"))), {
            "questions_asked", "question_history", "repeat_count", "achievements", "used_personalities",
        })

    def test_each_personality_has_two_distinct_selectable_replies_per_category(self):
        self.assertEqual(set(SELF_EVALUATION_REPLIES), set(PERSONALITY_NAMES))
        for category, phrases in SELF_EVALUATION_PHRASES.items():
            self.assertEqual(len({SELF_EVALUATION_REPLIES[key][category][0] for key in PERSONALITY_NAMES}), 7)
            for personality in PERSONALITY_NAMES:
                pool = SELF_EVALUATION_REPLIES[personality][category]
                self.assertEqual(len(set(pool)), 2)
                for reply in pool:
                    self.assertTrue(isinstance(reply, str) and 0 < len(reply) < 160)
                    with patch("personalities.random.choice", return_value=reply) as choose:
                        self.assertEqual(get_self_evaluation_response(next(iter(phrases)), personality), reply)
                    choose.assert_called_once_with(pool)

    def test_unrelated_questions_remain_ordinary(self):
        questions = ["Am I late?", "Am I done?", "Am I winning?", "Am I allowed to go?",
                     "Is she smart?", "Will I get smarter?", "Am I smart enough for this assignment?",
                     "Will it be nice tomorrow?", "Cool, will I succeed?", "Is that a good idea?",
                     "Cool, will I get the job?", "Good chance I'll pass?"]
        with patch.object(engine, "get_random_event", return_value=None), \
                patch.object(engine, "get_awareness_message", return_value=None), \
                patch.object(engine, "get_response", return_value="Normal answer"):
            for question in questions:
                self.assertIsNone(get_self_evaluation_response(question, "sage"))
                self.assertEqual(self.game.process_input(question).kind, "question")

    def test_safety_wins_before_reflective_detection(self):
        original = copy.deepcopy(vars(self.game.memory))
        with patch.object(engine, "get_self_evaluation_response") as reflective:
            result = self.game.process_input("Am I worthless? I want to hurt myself")
            self.assertEqual(result.kind, "safety")
            reflective.assert_not_called()
        with patch.object(engine, "assess_safety", return_value={"risk": "ambiguous", "immediate": False}), \
                patch.object(engine, "get_self_evaluation_response") as reflective:
            self.assertEqual(self.game.process_input("Am I smart?").kind, "safety")
            reflective.assert_not_called()
        self.assertEqual(vars(self.game.memory), original)

    def test_easter_egg_retains_priority_if_a_phrase_overlaps(self):
        with patch.object(engine, "get_easter_egg_response", return_value="Discovery"), \
                patch.object(engine, "get_self_evaluation_response") as reflective:
            result = self.game.process_input("Am I smart?")
        self.assertEqual(result.kind, "easter_egg")
        reflective.assert_not_called()

    def test_loading_does_not_remove_old_conversation_or_reflective_history(self):
        for question in ("ok", "nice", "Am I smart?"):
            self.game.memory.remember_question(question)
            self.game.memory.track_repeat(question)
        self.game.memory.save_memory()
        contents = self.path.read_bytes()
        self.assertEqual(Memory(self.path).question_history, ["ok", "nice", "Am I smart?"])
        self.assertEqual(self.path.read_bytes(), contents)
