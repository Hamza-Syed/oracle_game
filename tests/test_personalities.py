import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
import game as engine
from memories import Memory
from personalities import PERSONALITY_NAMES, RESPONSES, RESPONSE_POOLS, get_response, get_topic_reaction


class PersonalityTests(unittest.TestCase):
    def test_each_response_pool_has_five_positive_four_uncertain_three_negative(self):
        self.assertEqual(set(RESPONSE_POOLS), set(PERSONALITY_NAMES))
        for personality, categories in RESPONSE_POOLS.items():
            self.assertEqual({name: len(pool) for name, pool in categories.items()},
                             {"positive": 5, "uncertain": 4, "negative": 3})
            self.assertEqual(RESPONSES[personality], [answer for pool in categories.values() for answer in pool])
            for pool in categories.values():
                self.assertTrue(all(isinstance(answer, str) and answer.strip() for answer in pool))
                with patch("personalities.random.choice", return_value=pool[0]) as choose:
                    self.assertEqual(get_response(personality), pool[0])
                choose.assert_called_once_with(RESPONSES[personality])

    def setUp(self):
        clock = patch("achievements.get_current_hour", return_value=12)
        clock.start()
        self.addCleanup(clock.stop)
        events = patch("game.get_random_event", return_value=None)
        events.start()
        self.addCleanup(events.stop)

    def test_all_seven_personalities_can_be_selected(self):
        expected = ["sage", "student", "pirate", "fortune_teller", "wizard", "alien", "robot"]
        for number, key in enumerate(expected, start=1):
            with self.subTest(personality=key):
                output = io.StringIO()
                with patch("builtins.input", return_value=f" {number} "), \
                        contextlib.redirect_stdout(output):
                    self.assertEqual(main.choose_personality(), key)
                for menu_number, name in enumerate(PERSONALITY_NAMES.values(), start=1):
                    self.assertIn(f"{menu_number}. {name}", output.getvalue())

    def test_each_personality_has_twelve_distinct_selectable_answers(self):
        self.assertEqual(set(RESPONSES), set(PERSONALITY_NAMES))
        for key, responses in RESPONSES.items():
            with self.subTest(personality=key):
                self.assertEqual(len(responses), 12)
                self.assertEqual(len(set(responses)), 12)
                self.assertTrue(all(isinstance(answer, str) and answer.strip() for answer in responses))
                # Exercise every answer without depending on random selection.
                for answer in responses:
                    with patch("personalities.random.choice", return_value=answer) as choose:
                        self.assertEqual(get_response(key), answer)
                        choose.assert_called_once_with(responses)

    def check_topic(self, topic):
        reactions = [get_topic_reaction(key, topic) for key in PERSONALITY_NAMES]
        self.assertTrue(all(isinstance(reaction, str) and reaction.strip() for reaction in reactions))
        self.assertEqual(len(set(reactions)), 7)

    def test_all_personalities_support_exam(self):
        self.check_topic("exam")

    def test_all_personalities_support_job(self):
        self.check_topic("job")

    def test_all_personalities_support_internship(self):
        self.check_topic("internship")

    def test_invalid_selections_reprompt_and_quit_still_works(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["", "banana", "0", "8", "99", "7"]), \
                contextlib.redirect_stdout(output):
            self.assertEqual(main.choose_personality(), "robot")
        self.assertEqual(output.getvalue().count("Invalid selection"), 5)
        with patch("builtins.input", return_value=" QUIT "), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(main.choose_personality())

    def test_change_to_every_personality_updates_stats_without_changing_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.json"
            memory = Memory(path)
            memory.remember_question("Will I pass my exam?")
            memory.track_repeat("Will I pass my exam?")
            memory.achievements.add("First Question")
            memory.save_memory()
            memory = Memory(path)
            original_state = copy.deepcopy(vars(memory))
            original_save = path.read_bytes()
            inputs = ["1"]
            for number in range(1, 8):
                inputs.extend([" CHANGE ", str(number), "stats"])
            inputs.append("quit")
            output = io.StringIO()
            with patch.object(engine, "Memory", return_value=memory), \
                    patch("builtins.input", side_effect=inputs), \
                    contextlib.redirect_stdout(output):
                main.main()
            for name in PERSONALITY_NAMES.values():
                self.assertIn(f"Current personality: {name}", output.getvalue())
            # Five actual switches now award a secret; question progress is unchanged.
            original_state["achievements"].add("Personality Crisis")
            self.assertEqual(vars(memory), original_state)
            self.assertEqual(Memory(path).achievements, original_state["achievements"])

    def test_new_personalities_answer_questions_in_character(self):
        for number, key in enumerate(list(PERSONALITY_NAMES)[3:], start=4):
            with self.subTest(personality=key), tempfile.TemporaryDirectory() as directory:
                memory = Memory(Path(directory) / "memory.json")
                output = io.StringIO()
                with patch.object(engine, "Memory", return_value=memory), \
                        patch("builtins.input", side_effect=[
                            str(number), "An exam?", "A job?", "An internship?", "quit",
                        ]), \
                        patch("personalities.random.choice", side_effect=lambda pool: pool[0]), \
                        contextlib.redirect_stdout(output):
                    main.main()
                for topic in ("exam", "job", "internship"):
                    self.assertIn(get_topic_reaction(key, topic), output.getvalue())
                self.assertEqual(output.getvalue().count(RESPONSES[key][0]), 3)
                self.assertEqual(memory.questions_asked, 3)

    def test_unknown_personality_and_topic_keep_existing_fallbacks(self):
        self.assertEqual(get_response("unknown"), "The oracle is confused.")
        self.assertIsNone(get_topic_reaction("unknown", "exam"))
        for key in PERSONALITY_NAMES:
            self.assertIsNone(get_topic_reaction(key, "other"))


if __name__ == "__main__":
    unittest.main()
