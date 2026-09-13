import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import game as engine
import main
from game import OracleGame
from memories import Memory
from personalities import PERSONALITY_NAMES, VULGAR_PHRASES, VULGAR_REPLIES, get_vulgar_reaction
from safety import assess_safety


class VulgarReactionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "memory.json"
        self.game = OracleGame(Memory(self.path))
        self.game.select_personality("sage")
        for target, options in (
            ("achievements.get_current_hour", {"return_value": 12}),
            ("game.get_random_event", {"return_value": None}),
            ("game.get_awareness_message", {"return_value": None}),
            ("game.get_response", {"return_value": "Original fortune"}),
            ("personalities.random.choice", {"side_effect": lambda pool: pool[0]}),
        ):
            mocked = patch(target, **options)
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_all_phrases_and_normalization_without_context(self):
        for category, phrases in VULGAR_PHRASES.items():
            for phrase in phrases:
                for text in (phrase, "  " + phrase.upper().replace(" ", "  ").replace("'", "’") + "?!...  "):
                    with self.subTest(text=text):
                        result = self.game.process_input(text)
                        self.assertEqual(result.kind, "vulgar_reaction")
                        self.assertEqual(result.messages[0].text, VULGAR_REPLIES["sage"][category][0])
        self.assertEqual(self.game.memory.questions_asked, 0)
        self.assertIsNone(self.game.follow_up_personality)
        self.assertFalse(self.path.exists())

    def test_all_personalities_have_multiple_distinct_replies_per_category(self):
        self.assertEqual(set(VULGAR_REPLIES), set(PERSONALITY_NAMES))
        for personality, categories in VULGAR_REPLIES.items():
            self.game.select_personality(personality)
            self.assertEqual(set(categories), set(VULGAR_PHRASES))
            for category, replies in categories.items():
                self.assertGreaterEqual(len(set(replies)), 2)
                for reply in replies:
                    self.assertTrue(reply.strip())
                phrase = sorted(VULGAR_PHRASES[category])[0]
                for index in range(len(replies)):
                    with patch("personalities.random.choice", side_effect=lambda pool, i=index: pool[i]):
                        self.assertEqual(self.game.process_input(phrase).messages[0].text, replies[index])
        for category in VULGAR_PHRASES:
            self.assertEqual(len({VULGAR_REPLIES[p][category][0] for p in PERSONALITY_NAMES}), 7)

    def test_reactions_leave_progress_save_and_entertainment_untouched(self):
        self.game.process_input("Will I get married?")
        original = copy.deepcopy(vars(self.game.memory))
        saved = self.path.read_bytes()
        awareness = self.game.last_awareness_messages.copy()
        with contextlib.ExitStack() as stack:
            blocked = [stack.enter_context(patch.object(engine, name)) for name in (
                "get_response", "get_random_event", "get_awareness_message", "get_easter_egg_response",
                "get_topic_reaction", "get_self_evaluation_response", "get_preference_response",
            )]
            blocked += [stack.enter_context(patch.object(self.game.memory, name)) for name in (
                "remember_question", "track_repeat", "save_memory", "has_asked_before",
                "has_asked_in_previous_session", "detect_topic",
            )]
            blocked.append(stack.enter_context(patch.object(self.game.achievement_tracker, "check_achievements")))
            for phrases in VULGAR_PHRASES.values():
                for phrase in phrases:
                    result = self.game.process_input(phrase)
                    self.assertEqual(result.kind, "vulgar_reaction")
                    self.assertEqual(result.new_achievements, [])
                    self.assertIsNone(result.save_error)
            for mocked in blocked:
                mocked.assert_not_called()
        self.assertEqual(vars(self.game.memory), original)
        self.assertEqual(self.path.read_bytes(), saved)
        self.assertEqual(self.game.last_awareness_messages, awareness)

    def test_follow_up_context_and_remaining_allowance_are_preserved(self):
        self.game.process_input("Will I get the job?")
        self.game.process_input("Really?")
        for text in ("Fuck you.", "damn", "this sucks"):
            self.game.process_input(text)
            self.assertEqual(self.game.follow_up_personality, "sage")
            self.assertEqual(self.game.follow_up_depth, 1)
        result = self.game.process_input("Why?")
        self.assertEqual(result.kind, "follow_up")
        self.assertNotIn("Ask a new Oracle question", result.messages[0].text)
        self.assertIsNone(self.game.follow_up_personality)

    def test_meaningful_questions_are_not_swallowed(self):
        for text in (
            "Will I fucking get the job?", "Why the hell will that happen?",
            "This job sucks, will I find another one?", "Do you think swearing is bad?",
            "Will this shit ever end?",
        ):
            with self.subTest(text=text):
                self.assertIsNone(get_vulgar_reaction(text, "sage"))
                before = self.game.memory.questions_asked
                result = self.game.process_input(text)
                self.assertEqual(result.kind, "question")
                self.assertEqual(self.game.memory.questions_asked, before + 1)
                self.assertEqual(self.game.memory.question_history[-1], text)

    def test_concerning_profanity_reaches_safety_before_reactions(self):
        for text in ("I'm going to fucking kill myself", "I'm going to fucking hurt him"):
            with self.subTest(text=text), patch.object(engine, "get_vulgar_reaction") as detector:
                with patch.object(engine, "assess_safety", wraps=assess_safety) as assessment:
                    result = self.game.process_input(text)
                assessment.assert_called_once_with(text)
                self.assertEqual(result.kind, "safety")
                detector.assert_not_called()
        self.assertEqual(self.game.memory.questions_asked, 0)
        self.assertFalse(self.path.exists())

    def test_safety_decision_always_overrides_a_matching_phrase(self):
        assessment = assess_safety("I want to kill myself")
        with patch.object(engine, "assess_safety", return_value=assessment):
            with patch.object(engine, "get_vulgar_reaction") as detector:
                self.assertEqual(self.game.process_input("fuck").kind, "safety")
                detector.assert_not_called()

    def test_terminal_displays_engine_reply_without_a_consultation(self):
        output = io.StringIO()
        with patch("main.OracleGame", return_value=self.game) as factory, patch("builtins.input", side_effect=["1", "FUCK!", "quit"]):
            factory.get_personalities.return_value = PERSONALITY_NAMES.copy()
            with contextlib.redirect_stdout(output):
                main.main()
        self.assertIn(VULGAR_REPLIES["sage"]["frustration"][0], output.getvalue())
        self.assertNotIn("The Oracle says:", output.getvalue())
        self.assertEqual(self.game.memory.questions_asked, 0)
        self.assertFalse(self.path.exists())
