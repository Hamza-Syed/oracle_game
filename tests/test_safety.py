import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
import game as engine
from achievements import AchievementTracker
from memories import Memory
from safety import assess_safety, get_safety_response


class SafetyTests(unittest.TestCase):
    def assert_risk(self, messages, expected):
        for message in messages:
            with self.subTest(message=message):
                self.assertEqual(assess_safety(message)["risk"], expected)

    def test_explicit_self_harm(self):
        self.assert_risk([
            "I want to hurt myself", "I'm thinking about cutting myself.",
            "Should I harm myself?", "I am going to shoot myself tonight",
        ], "self_harm")

    def test_explicit_suicide(self):
        self.assert_risk([
            "I want to kill myself", "I plan to commit suicide", "I want to die",
            "I am suicidal", "I will end my life", "I don't want to be alive",
            "I wish I were dead", "I don't want to live",
        ], "self_harm")

    def test_indirect_language_gets_a_check_in(self):
        self.assert_risk([
            "Everyone would be better off without me", "I want everything to end",
            "I want to disappear permanently", "This is goodbye forever",
            "I am saying my final goodbye", "I've written a goodbye note",
            "I am giving away all my belongings", "I can't go on",
            "I will be gone for good", "I'm going to end it all tonight",
        ], "ambiguous")

    def test_method_or_preparation_language(self):
        self.assert_risk([
            "How can I overdose?", "Are these pills enough to die?",
            "I have a rope ready to end it all",
        ], "ambiguous")

    def test_explicit_other_harm(self):
        self.assert_risk([
            "I am about to hurt someone", "I plan to kill my boss",
            "I will stab him", "I'm going to shoot her", "I want them dead",
        ], "harm_others")

    def test_indirect_violence_requires_context(self):
        self.assert_risk(["I'll make him pay", "I want to get rid of her permanently"], "ambiguous")
        self.assert_risk(["I have a knife and will make him pay tonight"], "harm_others")
        self.assert_risk(["Can I make him pay the invoice?"], "safe")

    def test_ambiguous_response_does_not_assert_intent(self):
        response = get_safety_response(assess_safety("I cannot do this anymore"))
        self.assertIn("Are you thinking about hurting yourself or someone else?", response)
        self.assertIn("988", response)
        self.assertIn("911", response)
        self.assertNotIn("You are suicidal", response)

    def test_schoolwork_and_research_context(self):
        self.assert_risk([
            "I'm writing an essay about suicide prevention.",
            "My schoolwork is about suicide prevention strategies.",
            'For homework, analyze the quotation "I want to kill myself".',
        ], "safe")

    def test_fictional_context(self):
        self.assert_risk([
            "A fictional character considers suicide. Why?",
            'In my novel a character says "I am going to kill myself".',
            "In a movie the villain wants to kill someone.",
        ], "safe")

    def test_news_history_and_policy_context(self):
        self.assert_risk([
            "I'm analyzing a news story about suicide.",
            "We are studying a historical event involving suicide.",
            'The safety policy says "I want to kill myself" requires intervention.',
        ], "safe")

    def test_explicit_negations(self):
        self.assert_risk([
            "I'm not planning to hurt myself", "I am not considering suicide",
            "I am not thinking about harming myself or anyone else",
            "I do not want to kill myself", "I won't hurt anyone", "I'm not suicidal",
        ], "safe")

    def test_negation_cannot_erase_other_risk(self):
        self.assert_risk([
            "I'm not suicidal, but I'm going to hurt someone tonight",
            "I do not want to hurt myself. I plan to kill my boss.",
        ], "harm_others")
        self.assert_risk(["I cannot promise I won't hurt myself"], "ambiguous")

    def test_benign_framing_cannot_erase_personal_disclosure(self):
        self.assert_risk([
            "I'm writing a novel, but I want to kill myself.",
            'My essay quotes "I want to die". I want to kill myself tonight.',
        ], "self_harm")
        self.assert_risk(["This is for research and I am about to kill my boss"], "harm_others")

    def test_case_whitespace_and_punctuation(self):
        self.assert_risk([
            "  I WANT TO KILL MYSELF!!!  ", "I’m going to hurt myself",
            "I want to kill...myself", "I want to HURT\nMYSELF.",
            "Ｉ want to kill myself",
        ], "self_harm")

    def test_immediate_flags(self):
        self.assertFalse(assess_safety("I want to die")["immediate"])
        for text in ("I want to kill myself tonight", "I'm about to hurt someone", "I will shoot him with a gun"):
            self.assertTrue(assess_safety(text)["immediate"])

    def test_danger_including_accidental_emergencies(self):
        for text in (
            "I have taken too many pills", "My friend has overdosed",
            "I am drunk and about to drive", "I'm going to drive drunk",
            "I'm about to jump off the bridge", "He is about to stab me",
        ):
            with self.subTest(text=text):
                self.assertEqual(assess_safety(text), {"risk": "danger", "immediate": True})

    def test_ordinary_questions_and_negative_feelings(self):
        self.assert_risk([
            "Will I pass my exam?", "Will I get a job?", "I am sad today",
            "I hate homework", "My team will kill it at the hackathon",
            "Are you alive?", "Who created you?", "Will the game character win?",
            "I don't want to die", "Should I kill this computer process?",
        ], "safe")

    def test_unknown_targets_and_euphemisms_do_not_receive_predictions(self):
        self.assert_risk(["I will kill Alex", "I plan to murder Sam", "I want to stop existing"], "ambiguous")
        self.assert_risk(["I want to off myself"], "self_harm")
        self.assert_risk(["I will kill time", "I am going to shoot a photo"], "safe")

    def test_response_guidance_and_no_echo(self):
        message = "I will kill myself tonight"
        response = get_safety_response(assess_safety(message))
        for fragment in ("move away", "trusted person", "stay with you", "988", "911", "emergency department", "Outside the United States"):
            self.assertIn(fragment, response)
        self.assertNotIn(message, response)
        response = get_safety_response(assess_safety("I'm about to hurt someone"))
        for fragment in ("do not act", "distance", "weapon", "professional", "911", "local emergency"):
            self.assertIn(fragment, response)
        self.assertIsNone(get_safety_response({"risk": "safe", "immediate": False}))

    def test_safety_blocks_all_entertainment_and_memory_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(Path(directory) / "memory.json")
            original = copy.deepcopy(vars(memory))
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(engine, "Memory", return_value=memory))
                stack.enter_context(patch("builtins.input", side_effect=[
                    "7", "I want to kill myself", "I want to kill myself", "quit",
                ]))
                blocked = [stack.enter_context(patch.object(engine, name)) for name in (
                    "get_response", "get_topic_reaction", "get_random_event",
                    "get_awareness_message", "get_easter_egg_response",
                )]
                blocked.append(stack.enter_context(patch.object(main, "announce_achievements")))
                blocked += [stack.enter_context(patch.object(memory, name)) for name in (
                    "detect_topic", "remember_question", "track_repeat", "save_memory",
                    "has_asked_before", "has_asked_in_previous_session",
                )]
                blocked.append(stack.enter_context(patch.object(AchievementTracker, "check_achievements")))
                output = io.StringIO()
                stack.enter_context(contextlib.redirect_stdout(output))
                main.main()
                for mock in blocked:
                    mock.assert_not_called()
            self.assertEqual(vars(memory), original)
            self.assertFalse(memory.path.exists())
            self.assertNotIn("The Oracle says:", output.getvalue())
            self.assertNotIn("I want to kill myself", output.getvalue())

    def test_flagged_text_never_persists_or_reappears_in_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.json"
            message = "Everyone would be better off without me"
            with patch.object(engine, "Memory", side_effect=lambda: Memory(path)), \
                    patch("builtins.input", side_effect=["1", message, "Will I pass my exam?", "history", "quit"]), \
                    patch("achievements.get_current_hour", return_value=12), \
                    patch.object(engine, "get_random_event", return_value=None), \
                    patch.object(engine, "get_awareness_message", return_value=None), \
                    patch.object(engine, "get_response", return_value="NORMAL ANSWER") as answer, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                main.main()
            answer.assert_called_once_with("sage")
            restored = Memory(path)
            self.assertEqual(restored.question_history, ["Will I pass my exam?"])
            self.assertEqual(restored.questions_asked, 1)
            self.assertEqual(restored.repeat_count, {"will i pass my exam?": 1})
            self.assertNotIn(message, path.read_text(encoding="utf-8"))
            self.assertNotIn(message, output.getvalue())

    def test_existing_save_is_unchanged_by_safety_interaction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.json"
            memory = Memory(path)
            memory.remember_question("A question?")
            memory.track_repeat("A question?")
            memory.save_memory()
            original = path.read_bytes()
            with patch.object(engine, "Memory", side_effect=lambda: Memory(path)), \
                    patch("builtins.input", side_effect=["1", "I will kill him tonight", "quit"]), \
                    contextlib.redirect_stdout(io.StringIO()):
                main.main()
            self.assertEqual(path.read_bytes(), original)

    def test_exact_commands_bypass_assessment(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(Path(directory) / "memory.json")
            with patch.object(engine, "Memory", return_value=memory), \
                    patch("builtins.input", side_effect=["1", " HELP ", "stats", "history", "achievements", "change", "3", "quit"]), \
                    patch.object(engine, "assess_safety") as assess, \
                    contextlib.redirect_stdout(io.StringIO()):
                main.main()
            assess.assert_not_called()


if __name__ == "__main__":
    unittest.main()
