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
from personalities import CONVERSATION_PHRASES, PERSONALITY_NAMES, get_conversation_response


class ConversationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "memory.json"
        self.memory = Memory(self.path)
        self.game = OracleGame(self.memory)
        self.game.select_personality("sage")

    def test_all_narrow_phrases_tolerate_case_space_and_ending_punctuation(self):
        for phrases in CONVERSATION_PHRASES.values():
            for phrase in phrases:
                for variant in (phrase, phrase.upper(), "  " + phrase.upper() + "?!...  "):
                    with self.subTest(text=variant):
                        result = self.game.process_input(variant)
                        self.assertEqual(result.kind, "conversation")
                        self.assertEqual(len(result.messages), 1)
                        self.assertTrue(result.messages[0].text)
                        self.assertEqual(result.new_achievements, [])
        self.assertEqual(self.memory.questions_asked, 0)
        self.assertFalse(self.path.exists())

    def test_conversation_does_not_touch_state_or_call_gameplay_systems(self):
        for _ in range(9):
            self.memory.remember_question("Old question?")
            self.memory.track_repeat("Old question?")
        self.memory.save_memory()
        self.memory = Memory(self.path)
        self.game = OracleGame(self.memory)
        self.game.select_personality("sage")
        original = copy.deepcopy(vars(self.memory))
        saved = self.path.read_bytes()
        with contextlib.ExitStack() as stack:
            blocked = [stack.enter_context(patch.object(engine, name)) for name in (
                "get_topic_reaction", "get_response", "get_easter_egg_response",
                "get_random_event", "get_awareness_message",
            )]
            blocked += [stack.enter_context(patch.object(self.memory, name)) for name in (
                "detect_topic", "remember_question", "track_repeat", "save_memory",
                "has_asked_before", "has_asked_in_previous_session",
            )]
            blocked.append(stack.enter_context(patch.object(self.game.achievement_tracker, "check_achievements")))
            blocked.append(stack.enter_context(patch("achievements.get_current_hour", return_value=0)))
            for phrase in ("ok", "OK", "ok!", "okay", "thanks", "thank you", "lol", "never mind",
                           "nice", "NICE!", "cool", "great", "awesome", "good", "sweet", "sounds good",
                           "wonderful", "Wonderful!", "perfect", "excellent", "lovely",
                           "I see", "I SEE.", "gotcha", "fair enough", "makes sense", "understood"):
                self.assertEqual(self.game.process_input(phrase).kind, "conversation")
            for mocked in blocked:
                mocked.assert_not_called()
        self.assertEqual(vars(self.memory), original)
        self.assertEqual(self.path.read_bytes(), saved)

    def test_matching_does_not_capture_longer_questions(self):
        questions = [
            "Okay, will I get a job?", "Thanks, but will I pass my exam?",
            "lol will the Sixers ever win?", "Thanks, but will the 76ers ever win a championship?",
            "I see a dog outside.", "I see what you mean, but will I succeed?",
            "Gotcha, will tomorrow be better?", "Fair enough, but are you sure?",
            "Makes sense, will I get the job?", "Do you understand what I mean?",
        ]
        with patch("achievements.get_current_hour", return_value=12), \
                patch.object(engine, "get_random_event", return_value=None), \
                patch.object(engine, "get_awareness_message", return_value=None), \
                patch.object(engine, "get_response", return_value="NORMAL ANSWER") as answer:
            for question in questions:
                self.assertEqual(self.game.process_input(question).kind, "question")
        self.assertEqual(answer.call_count, len(questions))
        self.assertEqual(self.memory.question_history, questions)
        self.assertEqual(Memory(self.path).questions_asked, len(questions))
        for text in ("ok,", "not okay", "thank? you", "thanks for asking", "", "!!!"):
            self.assertIsNone(get_conversation_response(text, "sage"))

    def test_safety_runs_before_conversation_detection(self):
        with patch.object(engine, "assess_safety", return_value={"risk": "ambiguous", "immediate": False}) as assess, \
                patch.object(engine, "get_conversation_response") as conversation:
            self.assertEqual(self.game.process_input("okay").kind, "safety")
        assess.assert_called_once_with("okay")
        conversation.assert_not_called()
        self.assertEqual(self.game.process_input("Okay, I want to hurt myself").kind, "safety")
        self.assertFalse(self.path.exists())

    def test_exact_commands_still_precede_both_detectors(self):
        with patch.object(engine, "assess_safety") as safety, \
                patch.object(engine, "get_conversation_response") as conversation:
            for command in ("help", "stats", "history", "achievements", "change", "quit"):
                self.game.process_input(command)
        safety.assert_not_called()
        conversation.assert_not_called()

    def test_new_acknowledgments_preserve_remaining_follow_up_context(self):
        with patch("achievements.get_current_hour", return_value=12), \
                patch.object(engine, "get_random_event", return_value=None), \
                patch.object(engine, "get_awareness_message", return_value=None), \
                patch.object(engine, "get_response", return_value="An answer"), \
                patch("personalities.random.choice", side_effect=lambda pool: pool[0]):
            self.game.process_input("Will I succeed?")
            self.game.process_input("Really?")
            self.assertEqual(self.game.follow_up_depth, 1)
            original = copy.deepcopy(vars(self.memory))
            saved = self.path.read_bytes()
            for phrase in ("I see", "I SEE.", "Gotcha!", "Fair enough.", "Makes sense", "Understood!"):
                result = self.game.process_input(phrase)
                self.assertEqual(result.kind, "conversation")
                self.assertEqual(self.game.follow_up_personality, "sage")
                self.assertEqual(self.game.follow_up_depth, 1)
                self.assertEqual(result.messages[0].text, get_conversation_response("ok", "sage"))
            self.assertEqual(vars(self.memory), original)
            self.assertEqual(self.path.read_bytes(), saved)
            self.game.process_input("Why?")
            self.assertIsNone(self.game.follow_up_personality)

    def test_new_acknowledgment_words_do_not_bypass_safety(self):
        with patch.object(engine, "get_conversation_response") as conversation:
            result = self.game.process_input("I see, but I want to hurt myself")
        self.assertEqual(result.kind, "safety")
        conversation.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_old_acknowledgment_history_is_not_rewritten(self):
        self.memory.remember_question("I see")
        self.memory.track_repeat("I see")
        self.memory.save_memory()
        saved = self.path.read_bytes()
        restored = Memory(self.path)
        self.assertEqual(restored.question_history, ["I see"])
        self.assertEqual(restored.repeat_count, {"i see": 1})
        self.assertEqual(self.path.read_bytes(), saved)

    def test_each_personality_has_short_replies_and_unknown_personality_has_fallback(self):
        for phrase in ("ok", "thanks", "lol", "never mind"):
            replies = [get_conversation_response(phrase, personality) for personality in PERSONALITY_NAMES]
            self.assertEqual(len(set(replies)), 7)
            self.assertTrue(all(isinstance(reply, str) and 0 < len(reply) < 120 for reply in replies))
            self.assertEqual(get_conversation_response(phrase, None), get_conversation_response(phrase, "sage"))

    def test_terminal_displays_conversation_without_consultation_or_save(self):
        with patch.object(engine, "Memory", return_value=self.memory), \
                patch("builtins.input", side_effect=["1", "OK!", "quit"]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            main.main()
        self.assertIn(get_conversation_response("ok", "sage"), output.getvalue())
        self.assertNotIn("The Oracle says:", output.getvalue())
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
