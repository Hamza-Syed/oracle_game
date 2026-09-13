import contextlib
import io
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
import game as engine
from memories import Memory
from personalities import PERSONALITY_NAMES
from random_events import EVENTS, PERSONALITY_MESSAGES, get_random_event


class RandomEventTests(unittest.TestCase):
    def setUp(self):
        clock = patch("achievements.get_current_hour", return_value=12)
        clock.start()
        self.addCleanup(clock.stop)
        awareness = patch("game.get_awareness_message", return_value=None)
        awareness.start()
        self.addCleanup(awareness.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "memory.json"

    def select(self, roll, personality="sage", index=0):
        with patch("random_events.random.choice", side_effect=lambda pool: pool[index]):
            return get_random_event(personality, roll=roll)

    def play(self, inputs, event):
        output = io.StringIO()
        with patch.object(engine, "Memory", side_effect=lambda: Memory(self.path)), \
                patch("builtins.input", side_effect=inputs), \
                patch.object(engine, "get_random_event", return_value=event) as events, \
                patch.object(engine, "get_response", return_value="NORMAL ANSWER") as answer, \
                contextlib.redirect_stdout(output):
            main.main()
        return output.getvalue(), events, answer

    def test_normal_tier(self):
        self.assertIsNone(self.select(0.5))

    def test_uncommon_tier(self):
        self.assertEqual(self.select(0.95)["rarity"], "uncommon")

    def test_rare_tier(self):
        self.assertEqual(self.select(0.99)["rarity"], "rare")

    def test_extremely_rare_tier(self):
        self.assertEqual(self.select(0.999)["rarity"], "extremely_rare")

    def test_exact_boundaries(self):
        cases = [
            (0.0, None), (math.nextafter(0.90, 0), None),
            (0.90, "uncommon"), (math.nextafter(0.98, 0), "uncommon"),
            (0.98, "rare"), (math.nextafter(0.998, 0), "rare"),
            (0.998, "extremely_rare"), (math.nextafter(1.0, 0), "extremely_rare"),
        ]
        for roll, expected in cases:
            with self.subTest(roll=roll):
                event = self.select(roll)
                self.assertEqual(event["rarity"] if event else None, expected)

    def test_production_uses_one_rarity_roll(self):
        for roll in (0.5, 0.95, 0.99, 0.999):
            with patch("random_events.random.random", return_value=roll) as random_roll, \
                    patch("random_events.random.choice", side_effect=lambda pool: pool[0]) as choose:
                get_random_event("sage")
            random_roll.assert_called_once_with()
            self.assertEqual(choose.call_count, 0 if roll < 0.90 else 1)

    def test_uncommon_event_allows_normal_answer(self):
        event = self.select(0.95)
        output, events, answer = self.play(["1", "Will I pass my exam?", "quit"], event)
        self.assertTrue(event["show_normal_answer"])
        events.assert_called_once_with("sage")
        answer.assert_called_once_with("sage")
        self.assertLess(output.index(event["message"]), output.index("NORMAL ANSWER"))

    def test_replacement_event_skips_normal_answer(self):
        event = self.select(0.99)
        output, _, answer = self.play(["1", "Will I pass my exam?", "quit"], event)
        self.assertFalse(event["show_normal_answer"])
        self.assertIn(event["message"], output)
        self.assertNotIn("NORMAL ANSWER", output)
        answer.assert_not_called()

    def test_personality_wording(self):
        for roll in (0.95, 0.99, 0.999):
            messages = [self.select(roll, personality)["message"] for personality in PERSONALITY_NAMES]
            self.assertEqual(len(set(messages)), 7)

    def test_replacements_preserve_saved_questions_repeats_and_achievements(self):
        event = self.select(0.999)
        question = "Will I pass my exam?"
        output, events, _ = self.play(["1"] + [question] * 5 + ["quit"], event)
        self.assertEqual(events.call_count, 5)
        saved = Memory(self.path)
        self.assertEqual(saved.questions_asked, 5)
        self.assertEqual(saved.question_history, [question] * 5)
        self.assertEqual(saved.repeat_count, {question.lower(): 5})
        self.assertEqual(saved.achievements, {"First Question", "The Doubter"})
        self.assertIn("The Oracle senses academic uncertainty.", output)
        self.assertIn("You seek certainty where none exists.", output)
        self.assertIn("The Doubter UNLOCKED!", output)
        output, events, _ = self.play(["3", question.upper(), "stats", "quit"], event)
        events.assert_called_once_with("pirate")
        saved = Memory(self.path)
        self.assertEqual(saved.questions_asked, 6)
        self.assertEqual(saved.repeat_count[question.lower()], 6)
        self.assertEqual(saved.question_history[-1], question.upper())
        self.assertIn("Déjà Vu UNLOCKED!", output)
        self.assertNotIn("First Question UNLOCKED!", output)
        self.assertNotIn("The Doubter UNLOCKED!", output)
        self.assertIn("Current personality: Pirate", output)

    def test_commands_and_blank_input_never_trigger_events(self):
        _, events, answer = self.play([
            "1", " HELP ", " STATS ", " HISTORY ", " ACHIEVEMENTS ",
            " CHANGE ", "7", "", " QUIT ",
        ], self.select(0.999))
        events.assert_not_called()
        answer.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_no_event_preserves_normal_interaction(self):
        output, events, answer = self.play(["1", "Will I get a job?", "quit"], None)
        events.assert_called_once_with("sage")
        answer.assert_called_once_with("sage")
        self.assertIn("The future of your career concerns you.", output)
        self.assertIn("First Question UNLOCKED!", output)
        self.assertIn("The Oracle says:\nNORMAL ANSWER", output)
        self.assertEqual(Memory(self.path).questions_asked, 1)

    def test_all_event_variants_have_valid_results(self):
        for rarity, roll in (("uncommon", 0.95), ("rare", 0.99), ("extremely_rare", 0.999)):
            for index, (name, default, allow_answer) in enumerate(EVENTS[rarity]):
                for personality in [*PERSONALITY_NAMES, "unknown"]:
                    event = self.select(roll, personality, index)
                    self.assertEqual(event["rarity"], rarity)
                    self.assertEqual(event["show_normal_answer"], allow_answer)
                    self.assertEqual(event["message"],
                                     PERSONALITY_MESSAGES.get(name, {}).get(personality, default))
                    self.assertTrue(event["message"].strip())

    def test_invalid_rolls_fail_clearly(self):
        for roll in (-0.1, 1.0, float("nan")):
            with self.assertRaises(ValueError):
                get_random_event("sage", roll=roll)


if __name__ == "__main__":
    unittest.main()
