import contextlib
import copy
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
import game as engine
from achievements import AchievementTracker
from commands import show_stats
from memories import Memory
from personalities import PERSONALITY_NAMES
from self_awareness import MESSAGES, STAGES, get_awareness_message, get_awareness_stage


class SelfAwarenessTests(unittest.TestCase):
    def test_active_pools_have_four_distinct_concise_lines(self):
        self.assertEqual(set(MESSAGES), {stage for _, stage, _ in STAGES[1:]})
        for stage, personalities in MESSAGES.items():
            self.assertEqual(set(personalities), set(PERSONALITY_NAMES))
            for lines in personalities.values():
                self.assertEqual(len(lines), 4)
                self.assertEqual(len(set(lines)), 4)
                self.assertTrue(all(isinstance(line, str) and 0 < len(line) < 180 for line in lines))

    def test_previous_line_is_excluded_only_after_successful_roll(self):
        for count, stage, chance in STAGES[1:]:
            for personality, pool in MESSAGES[stage].items():
                previous = pool[0]
                with patch("self_awareness.random.choice", side_effect=lambda choices: choices[0]) as choose:
                    result = get_awareness_message(personality, count, roll=0, previous_message=previous)
                    self.assertNotEqual(result, previous)
                    choose.assert_called_once_with(pool[1:])
                with patch("self_awareness.random.choice") as choose:
                    self.assertIsNone(get_awareness_message(personality, count, roll=chance, previous_message=previous))
                    choose.assert_not_called()

    def test_single_line_pool_falls_back_without_changing_trigger(self):
        with patch.dict(MESSAGES["Noticing"], {"sage": ["Only line"]}), \
                patch("self_awareness.random.choice", side_effect=lambda pool: pool[0]):
            self.assertEqual(get_awareness_message("sage", 25, roll=0, previous_message="Only line"), "Only line")
            self.assertIsNone(get_awareness_message("sage", 25, roll=.05, previous_message="Only line"))

    def test_engine_remembers_last_line_per_personality_stage_only_in_session(self):
        memory = Memory(self.path)
        memory.questions_asked = 25
        game = engine.OracleGame(memory)
        game.select_personality("sage")
        def forced(personality, count, **options):
            return get_awareness_message(personality, count, roll=0, **options)
        def consult():
            result = game.process_input("A question?")
            return next(message.text for message in result.messages if message.role == "awareness")
        with patch.object(engine, "get_awareness_message", side_effect=forced), \
                patch.object(engine, "get_random_event", return_value=None), \
                patch.object(engine, "get_response", return_value="Normal answer"), \
                patch("self_awareness.random.choice", side_effect=lambda pool: pool[0]):
            first = consult()
            game.select_personality("pirate")
            consult()
            game.select_personality("sage")
            self.assertNotEqual(consult(), first)
            previous = game.last_awareness_messages.copy()
            memory.questions_asked = 49
            self.assertEqual(consult(), MESSAGES["Curious"]["sage"][0])
            self.assertEqual(game.last_awareness_messages[("sage", "Noticing")], previous[("sage", "Noticing")])
        self.assertEqual(engine.OracleGame(Memory(self.path)).last_awareness_messages, {})
        self.assertEqual(set(json.loads(self.path.read_text(encoding="utf-8"))), {
            "questions_asked", "question_history", "repeat_count", "achievements", "used_personalities",
        })

    def test_failed_roll_does_not_forget_previous_line_or_force_transition_dialogue(self):
        memory = Memory(self.path)
        memory.questions_asked = 49
        game = engine.OracleGame(memory)
        game.select_personality("sage")
        previous = MESSAGES["Curious"]["sage"][0]
        game.last_awareness_messages[("sage", "Curious")] = previous
        with patch.object(engine, "get_random_event", return_value=None), \
                patch.object(engine, "get_response", return_value="Normal"), \
                patch("self_awareness.random.random", return_value=.99) as roll, \
                patch("self_awareness.random.choice") as choose:
            result = game.process_input("A question?")
        roll.assert_called_once_with()
        choose.assert_not_called()
        self.assertNotIn("awareness", [message.role for message in result.messages])
        self.assertEqual(game.last_awareness_messages, {("sage", "Curious"): previous})

    def test_suppressed_interactions_leave_session_awareness_state_unchanged(self):
        memory = Memory(self.path)
        memory.questions_asked = 500
        game = engine.OracleGame(memory)
        game.select_personality("sage")
        original = {("sage", "Aware"): MESSAGES["Aware"]["sage"][0]}
        game.last_awareness_messages.update(original)
        event = {"message": "Special", "rarity": "extremely_rare", "show_normal_answer": False}
        with patch.object(engine, "get_awareness_message") as awareness, \
                patch.object(engine, "get_random_event", return_value=event), \
                patch("personalities.random.choice", side_effect=lambda pool: pool[0]):
            for text in ("help", "", "okay", "Are you real?", "Am I smart?", "Do you like water?",
                         "I want to hurt myself", "A normal question?"):
                game.process_input(text)
        awareness.assert_not_called()
        self.assertEqual(game.last_awareness_messages, original)

    def setUp(self):
        clock = patch("achievements.get_current_hour", return_value=12)
        clock.start()
        self.addCleanup(clock.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "memory.json"

    def seed(self, count):
        memory = Memory(self.path)
        for _ in range(count):
            memory.remember_question("Will I pass my exam?")
            memory.track_repeat("Will I pass my exam?")
        AchievementTracker().check_achievements(memory, count)
        memory.save_memory()
        return memory

    def play(self, inputs, roll=0, event=None):
        output = io.StringIO()
        with patch.object(engine, "Memory", side_effect=lambda: Memory(self.path)), \
                patch("builtins.input", side_effect=inputs), \
                patch.object(engine, "get_random_event", return_value=event), \
                patch.object(engine, "get_awareness_message", side_effect=lambda personality, count:
                             get_awareness_message(personality, count, roll=roll)) as awareness, \
                patch("self_awareness.random.choice", side_effect=lambda pool: pool[0]), \
                patch.object(engine, "get_response", return_value="NORMAL ANSWER") as answer, \
                contextlib.redirect_stdout(output):
            main.main()
        return output.getvalue(), awareness, answer

    def test_all_stage_boundaries(self):
        for count, name in (
            (0, "Dormant"), (24, "Dormant"), (25, "Noticing"), (49, "Noticing"),
            (50, "Curious"), (99, "Curious"), (100, "Questioning"), (249, "Questioning"),
            (250, "Awakening"), (499, "Awakening"), (500, "Aware"), (10000, "Aware"),
        ):
            with self.subTest(count=count):
                self.assertEqual(get_awareness_stage(count), name)

    def test_dormant_never_rolls_or_produces_dialogue(self):
        with patch("self_awareness.random.random") as roll, \
                patch("self_awareness.random.choice") as choose:
            for count in range(25):
                self.assertIsNone(get_awareness_message("sage", count, roll=0))
                self.assertIsNone(get_awareness_message("sage", count))
        roll.assert_not_called()
        choose.assert_not_called()

    def test_every_stage_and_personality_has_selectable_wording(self):
        for count, stage, chance in STAGES[1:]:
            self.assertEqual(set(MESSAGES[stage]), set(PERSONALITY_NAMES))
            first_messages = set()
            for personality in PERSONALITY_NAMES:
                for message in MESSAGES[stage][personality]:
                    self.assertTrue(message.strip())
                    with patch("self_awareness.random.choice", return_value=message):
                        self.assertEqual(get_awareness_message(personality, count, roll=0), message)
                first_messages.add(MESSAGES[stage][personality][0])
            self.assertEqual(len(first_messages), 7)

    def test_trigger_probability_boundaries(self):
        for count, stage, chance in STAGES[1:]:
            with self.subTest(stage=stage), \
                    patch("self_awareness.random.choice", side_effect=lambda pool: pool[0]):
                self.assertIsNotNone(get_awareness_message("sage", count, roll=math.nextafter(chance, 0)))
                self.assertIsNone(get_awareness_message("sage", count, roll=chance))
                self.assertIsNone(get_awareness_message("sage", count, roll=0.999))

    def test_awareness_is_read_only(self):
        memory = self.seed(500)
        state = copy.deepcopy(vars(memory))
        saved = self.path.read_bytes()
        with patch("self_awareness.random.choice", side_effect=lambda pool: pool[0]):
            get_awareness_message("robot", memory.questions_asked, roll=0)
        self.assertEqual(vars(memory), state)
        self.assertEqual(self.path.read_bytes(), saved)

    def test_real_question_counts_once_and_persists_across_restart(self):
        memory = self.seed(24)
        previous_achievements = memory.achievements.copy()
        output, awareness, answer = self.play(["1", "Will I pass my exam?", "quit"])
        awareness.assert_called_once_with("sage", 25)
        answer.assert_called_once_with("sage")
        self.assertIn(MESSAGES["Noticing"]["sage"][0], output)
        restored = Memory(self.path)
        self.assertEqual(restored.questions_asked, 25)
        self.assertEqual(restored.question_history, ["Will I pass my exam?"] * 25)
        self.assertEqual(restored.repeat_count, {"will i pass my exam?": 25})
        self.assertEqual(restored.achievements, previous_achievements | {"Déjà Vu"})
        self.assertEqual(get_awareness_stage(restored.questions_asked), "Noticing")
        self.assertEqual(set(json.loads(self.path.read_text(encoding="utf-8"))),
                         {"questions_asked", "question_history", "repeat_count", "achievements", "used_personalities"})
        output, awareness, _ = self.play(["3", "Will I get a job?", "quit"])
        awareness.assert_called_once_with("pirate", 26)
        self.assertIn(MESSAGES["Noticing"]["pirate"][0], output)

    def test_commands_and_blank_input_never_trigger_awareness(self):
        self.seed(500)
        saved = self.path.read_bytes()
        _, awareness, answer = self.play([
            "1", " HELP ", " STATS ", " HISTORY ", " ACHIEVEMENTS ",
            " CHANGE ", "7", "", " QUIT ",
        ])
        awareness.assert_not_called()
        answer.assert_not_called()
        self.assertEqual(self.path.read_bytes(), saved)

    def test_stats_shows_only_current_stage_without_triggering_dialogue(self):
        for count, name, chance in STAGES:
            memory = Memory(self.path)
            memory.questions_asked = count
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                show_stats(memory, "sage", AchievementTracker())
            stage_lines = [line for line in output.getvalue().splitlines() if "Awareness" in line]
            self.assertEqual(stage_lines, [f"Awareness stage: {name}"])
            self.assertNotIn("%", output.getvalue())
            self.assertNotIn("until", output.getvalue())

    def test_extremely_rare_event_suppresses_awareness(self):
        self.seed(500)
        event = {"message": "SPECIAL EVENT", "rarity": "extremely_rare", "show_normal_answer": False}
        output, awareness, answer = self.play(["1", "A question?", "quit"], event=event)
        awareness.assert_not_called()
        answer.assert_not_called()
        self.assertIn("SPECIAL EVENT", output)
        self.assertEqual(Memory(self.path).questions_asked, 501)

    def test_other_events_allow_awareness_with_clear_output_order(self):
        self.seed(99)
        for rarity, normal in (("uncommon", True), ("rare", False)):
            event = {"message": "SPECIAL EVENT", "rarity": rarity, "show_normal_answer": normal}
            output, awareness, answer = self.play(["1", "Will I pass my exam?", "quit"], event=event)
            self.assertEqual(awareness.call_count, 1)
            self.assertEqual(answer.call_count, int(normal))
            message = MESSAGES["Questioning"]["sage"][0]
            self.assertLess(output.index("The Oracle senses"), output.index("SPECIAL EVENT"))
            self.assertLess(output.index("You seek certainty"), output.index("SPECIAL EVENT"))
            self.assertLess(output.index("SPECIAL EVENT"), output.index(message))
            if normal:
                self.assertIn("Oracle Addict UNLOCKED!", output)
                self.assertLess(output.index(message), output.index("NORMAL ANSWER"))

    def test_no_awareness_keeps_normal_answer_even_at_stage_boundary(self):
        self.seed(24)
        output, _, answer = self.play(["1", "Will I pass my exam?", "quit"], roll=0.99)
        answer.assert_called_once_with("sage")
        self.assertIn("The Oracle says:\nNORMAL ANSWER", output)
        self.assertNotIn(MESSAGES["Noticing"]["sage"][0], output)

    def test_production_event_and_awareness_use_separate_rolls(self):
        self.seed(499)
        output = io.StringIO()
        # First value is the event roll, second is the awareness roll.
        with patch.object(engine, "Memory", side_effect=lambda: Memory(self.path)), \
                patch("builtins.input", side_effect=["1", "A question?", "quit"]), \
                patch("random.random", side_effect=[0.5, 0.0]) as rolls, \
                patch("random.choice", side_effect=lambda pool: pool[0]), \
                patch.object(engine, "get_response", return_value="NORMAL ANSWER"), \
                contextlib.redirect_stdout(output):
            main.main()
        self.assertEqual(rolls.call_count, 2)
        self.assertIn(MESSAGES["Aware"]["sage"][0], output.getvalue())


if __name__ == "__main__":
    unittest.main()
