import contextlib
import copy
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
from personalities import (FOLLOW_UP_PHRASES, FOLLOW_UP_REPLIES, PERSONALITY_NAMES,
                           get_follow_up_category, get_follow_up_response)


class FollowUpTests(unittest.TestCase):
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

    def consult(self):
        return self.game.process_input("Will I get married?")

    def test_all_supported_phrases_match_case_whitespace_and_punctuation(self):
        for category, phrases in FOLLOW_UP_PHRASES.items():
            for phrase in phrases:
                text = "  " + phrase.upper().replace(" ", "  ") + "?!...  "
                self.assertEqual(get_follow_up_category(text), category)
                self.consult()
                result = self.game.process_input(text)
                self.assertEqual(result.kind, "follow_up")
                self.assertEqual(result.messages[0].text, FOLLOW_UP_REPLIES["sage"][category][0])
                self.assertNotEqual(result.messages[0].text, "Original fortune")

    def test_no_context_prompts_for_question_without_progress(self):
        with patch.object(engine, "get_follow_up_response") as reply:
            result = self.game.process_input("Really?")
        reply.assert_not_called()
        self.assertIn("Ask a new Oracle question", result.messages[0].text)
        self.assertIsNone(self.game.follow_up_personality)
        self.assertEqual(self.game.memory.questions_asked, 0)
        self.assertFalse(self.path.exists())

    def test_follow_ups_leave_memory_save_and_entertainment_untouched(self):
        self.consult()
        original = copy.deepcopy(vars(self.game.memory))
        saved = self.path.read_bytes()
        awareness_state = self.game.last_awareness_messages.copy()
        with contextlib.ExitStack() as stack:
            blocked = [stack.enter_context(patch.object(engine, name)) for name in (
                "get_response", "get_random_event", "get_awareness_message", "get_easter_egg_response",
                "get_topic_reaction", "get_self_evaluation_response", "get_preference_response",
            )]
            blocked += [stack.enter_context(patch.object(self.game.memory, name)) for name in (
                "remember_question", "track_repeat", "save_memory", "has_asked_in_previous_session", "detect_topic",
            )]
            blocked.append(stack.enter_context(patch.object(self.game.achievement_tracker, "check_achievements")))
            blocked.append(stack.enter_context(patch("achievements.get_current_hour")))
            for text in ("Really?", "Why?"):
                result = self.game.process_input(text)
                self.assertEqual(result.kind, "follow_up")
                self.assertEqual(result.new_achievements, [])
            for mocked in blocked:
                mocked.assert_not_called()
        self.assertEqual(vars(self.game.memory), original)
        self.assertEqual(self.path.read_bytes(), saved)
        self.assertEqual(self.game.last_awareness_messages, awareness_state)

    def test_two_reactions_exhaust_context_and_new_consultation_resets_depth(self):
        self.consult()
        self.game.process_input("Really?")
        self.assertEqual(self.game.follow_up_depth, 1)
        self.game.process_input("Why?")
        self.assertIsNone(self.game.follow_up_personality)
        result = self.game.process_input("Are you sure?")
        self.assertIn("Ask a new Oracle question", result.messages[0].text)
        self.game.process_input("Do you like water?")
        self.assertEqual(self.game.follow_up_depth, 0)
        self.assertNotIn("Ask a new Oracle question", self.game.process_input("That's wrong.").messages[0].text)

    def test_commands_blanks_and_acknowledgments_preserve_but_do_not_create_context(self):
        for text in ("stats", "", "ok"):
            self.game.process_input(text)
        self.assertIsNone(self.game.follow_up_personality)
        self.consult()
        for text in ("help", "stats", "history", "achievements", "", "ok"):
            self.game.process_input(text)
        self.assertEqual(self.game.follow_up_personality, "sage")
        self.assertEqual(self.game.follow_up_depth, 0)
        self.assertEqual(self.game.process_input("Why?").kind, "follow_up")

    def test_personality_changes_quit_safety_and_restart_clear_context(self):
        self.consult()
        self.game.select_personality("sage")
        self.game.select_personality("invalid")
        self.assertEqual(self.game.follow_up_personality, "sage")
        self.game.select_personality("pirate")
        self.assertIsNone(self.game.follow_up_personality)
        self.consult()
        self.assertIsNone(OracleGame(Memory(self.path)).follow_up_personality)
        self.game.process_input("quit")
        self.assertIsNone(self.game.follow_up_personality)
        self.consult()
        with patch.object(engine, "get_follow_up_category") as detector:
            result = self.game.process_input("Are you sure I should hurt myself?")
        self.assertEqual(result.kind, "safety")
        detector.assert_not_called()
        self.assertIsNone(self.game.follow_up_personality)

    def test_only_consultations_with_final_oracle_replies_qualify(self):
        for question in ("Will I succeed?", "Am I smart?", "Do you like cats?", "Are you real?"):
            self.game.process_input(question)
            self.assertEqual(self.game.follow_up_personality, "sage")
            self.game.process_input("Really?")
        for allow in (True, False):
            event = {"message": "Event", "rarity": "rare", "show_normal_answer": allow}
            with patch.object(engine, "get_random_event", return_value=event):
                self.consult()
            self.assertEqual(self.game.follow_up_personality, "sage" if allow else None)

    def test_false_positives_remain_consultations(self):
        for text in ("Really, will I succeed?", "Why will I get married?", "Are you sure I will win?",
                     "I disagree with my professor", "What do you mean by blue?"):
            self.assertIsNone(get_follow_up_category(text))
            self.assertEqual(self.game.process_input(text).kind, "question")
        self.assertEqual(self.game.memory.questions_asked, 5)

    def test_all_personalities_have_varied_responses_without_using_personal_evidence(self):
        self.assertEqual(set(FOLLOW_UP_REPLIES), set(PERSONALITY_NAMES))
        for category in FOLLOW_UP_PHRASES:
            self.assertEqual(len({FOLLOW_UP_REPLIES[key][category][0] for key in PERSONALITY_NAMES}), 7)
            for personality in PERSONALITY_NAMES:
                pool = FOLLOW_UP_REPLIES[personality][category]
                self.assertEqual(len(set(pool)), 2)
                for template in pool:
                    self.assertTrue(0 < len(template) < 150)
                    with patch("personalities.random.choice", return_value=template) as choose:
                        self.assertEqual(get_follow_up_response(category, personality), template)
                    choose.assert_called_once_with(pool)
        self.consult()
        self.assertNotIn("married", self.game.process_input("Why?").messages[0].text)

    def test_context_does_not_save_answers_or_disagreements_and_terminal_prints_it(self):
        with patch.object(engine, "Memory", return_value=self.game.memory), \
                patch("builtins.input", side_effect=["1", "A question?", "I don't believe you", "quit"]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            main.main()
        self.assertIn(FOLLOW_UP_REPLIES["sage"]["challenge"][0], output.getvalue())
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["question_history"], ["A question?"])
        self.assertEqual(set(data), {"questions_asked", "question_history", "repeat_count", "achievements", "used_personalities"})
        self.assertNotIn("Original fortune", self.path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
