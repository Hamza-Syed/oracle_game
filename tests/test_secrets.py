import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
import game as engine
from achievements import AchievementTracker
from commands import show_achievements, show_help, show_stats
from easter_eggs import TRIGGERS, get_easter_egg_response
from memories import Memory
from personalities import PERSONALITY_NAMES


class SecretTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "memory.json"
        self.memory = Memory(self.path)
        self.tracker = AchievementTracker()

    def capture(self, function, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            function(*args)
        return output.getvalue()

    def ask(self, question="Will I pass my exam?", personality="sage", hour=12):
        previous = self.memory.has_asked_in_previous_session(question)
        self.memory.remember_question(question)
        repeat = self.memory.track_repeat(question)
        self.memory.used_personalities.add(personality)
        return self.tracker.check_achievements(
            self.memory, repeat, current_hour=hour, asked_previous_session=previous,
        )

    def play(self, inputs, hour=12):
        with patch.object(engine, "Memory", side_effect=lambda: Memory(self.path)), \
                patch("builtins.input", side_effect=inputs), \
                patch("achievements.get_current_hour", return_value=hour) as clock, \
                patch.object(engine, "get_random_event", return_value=None) as events, \
                patch.object(engine, "get_awareness_message", return_value=None) as awareness, \
                patch.object(engine, "get_response", return_value="NORMAL ANSWER") as answer:
            output = self.capture(main.main)
        return output, clock, events, awareness, answer

    def test_night_owl_unlocks_at_all_hours_inside_window(self):
        for hour in range(5):
            with self.subTest(hour=hour):
                self.memory = Memory(self.path)
                self.assertIn("Night Owl", self.ask(hour=hour))
                self.assertNotIn("Night Owl", self.ask(hour=hour))

    def test_night_owl_does_not_unlock_outside_window(self):
        for hour in range(5, 24):
            with self.subTest(hour=hour):
                self.assertNotIn("Night Owl", self.ask(hour=hour))
        self.assertNotIn("Night Owl", self.memory.achievements)

    def test_night_owl_real_question_uses_injected_clock(self):
        output, clock, _, _, _ = self.play(["1", "A question?", "quit"], hour=0)
        clock.assert_called_once_with()
        self.assertIn("Night Owl UNLOCKED!", output)
        self.assertIn("Night Owl", Memory(self.path).achievements)

    def test_commands_and_blank_input_cannot_unlock_night_owl(self):
        output, clock, events, awareness, answer = self.play([
            "1", " HELP ", " STATS ", " HISTORY ", " ACHIEVEMENTS ",
            " CHANGE ", "2", "", " QUIT ",
        ], hour=2)
        clock.assert_not_called()
        events.assert_not_called()
        awareness.assert_not_called()
        answer.assert_not_called()
        self.assertNotIn("Night Owl", output)
        self.assertFalse(self.path.exists())

    def test_indecisive_unlocks_on_tenth_repeat_only_once(self):
        for number in range(1, 12):
            question = "Will I pass my exam?" if number % 2 else " WILL I PASS MY EXAM? "
            unlocked = self.ask(question)
            self.assertEqual("Indecisive" in unlocked, number == 10)
        self.assertEqual(self.memory.repeat_count["will i pass my exam?"], 11)

    def test_personality_crisis_counts_only_actual_changes(self):
        self.assertEqual(self.tracker.record_personality_change(self.memory, None, "sage"), [])
        for selected in ("sage", "invalid", None):
            self.assertEqual(self.tracker.record_personality_change(self.memory, "sage", selected), [])
        self.assertEqual(self.tracker.personality_changes, 0)
        current = "sage"
        for count, selected in enumerate(["student", "pirate", "wizard", "alien", "robot", "sage"], 1):
            unlocked = self.tracker.record_personality_change(self.memory, current, selected)
            self.assertEqual(unlocked, ["Personality Crisis"] if count == 5 else [])
            current = selected
        self.assertEqual(self.memory.questions_asked, 0)
        self.assertEqual(self.memory.question_history, [])
        self.assertEqual(self.memory.repeat_count, {})
        self.assertEqual(self.memory.used_personalities, set())
        self.assertEqual(self.memory.achievements, {"Personality Crisis"})

    def test_personality_crisis_persists_immediately_without_questions(self):
        output, clock, events, awareness, answer = self.play([
            "1", "change", "bad", "1", "change", "2", "change", "3",
            "change", "4", "change", "5", "change", "6", "change", "7", "quit",
        ], hour=1)
        self.assertEqual(output.count("Personality Crisis UNLOCKED!"), 1)
        self.assertIn("Invalid selection", output)
        restored = Memory(self.path)
        self.assertEqual(restored.achievements, {"Personality Crisis"})
        self.assertEqual(restored.questions_asked, 0)
        self.assertEqual(restored.used_personalities, set())
        for mock in (clock, events, awareness, answer):
            mock.assert_not_called()

    def test_personality_change_counter_resets_each_session(self):
        first = ["1", "change", "2", "change", "3", "change", "4", "change", "5", "quit"]
        output, *_ = self.play(first)
        self.assertNotIn("UNLOCKED!", output)
        output, *_ = self.play(["1", "change", "2", "quit"])
        self.assertNotIn("UNLOCKED!", output)
        self.assertFalse(self.path.exists())

    def test_curious_mortal_unlocks_at_250_only_once(self):
        for count in range(1, 252):
            unlocked = self.ask(f"Question {count}?")
            self.assertEqual("Curious Mortal" in unlocked, count == 250)

    def test_completionist_requires_all_seven_actual_personality_uses(self):
        for count, personality in enumerate(PERSONALITY_NAMES, 1):
            unlocked = self.ask(personality=personality)
            self.assertEqual("Completionist" in unlocked, count == 7)
        self.assertNotIn("Completionist", self.ask())

    def test_completionist_and_personality_use_persist_across_sessions(self):
        for number in range(1, 8):
            output, *_ = self.play([str(number), f"Question {number}?", "quit"])
            self.assertEqual("Completionist UNLOCKED!" in output, number == 7)
        restored = Memory(self.path)
        self.assertEqual(restored.used_personalities, set(PERSONALITY_NAMES))
        self.assertIn("Completionist", restored.achievements)
        output, *_ = self.play(["7", "Another question?", "quit"])
        self.assertNotIn("Completionist UNLOCKED!", output)

    def test_older_save_defaults_personality_use_and_preserves_history(self):
        old_save = {
            "questions_asked": 1, "question_history": ["A question?"],
            "repeat_count": {"a question?": 1}, "achievements": ["First Question"],
        }
        self.path.write_text(json.dumps(old_save), encoding="utf-8")
        restored = Memory(self.path)
        self.assertEqual(restored.used_personalities, set())
        self.assertTrue(restored.has_asked_in_previous_session(" A QUESTION? "))
        restored.save_memory()
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved, dict(old_save, used_personalities=[]))

    def test_invalid_personality_use_data_does_not_overwrite_save(self):
        for value in ("sage", [123], None):
            self.path.write_text(json.dumps({"used_personalities": value}), encoding="utf-8")
            saved = self.path.read_bytes()
            output, *_ = self.play(["quit"])
            self.assertNotIn("Could not load memory", output)
            self.assertEqual(Memory(self.path).used_personalities, set())
            self.assertEqual(self.path.read_bytes(), saved)

    def test_deja_vu_uses_previous_session_history(self):
        self.ask()
        self.memory.save_memory()
        self.memory = Memory(self.path)
        self.assertIn("Déjà Vu", self.ask(" WILL I PASS MY EXAM? "))
        self.assertNotIn("Déjà Vu", self.ask())

    def test_deja_vu_does_not_use_repeats_or_saves_within_current_session(self):
        for _ in range(3):
            self.assertNotIn("Déjà Vu", self.ask())
            self.memory.save_memory()
        self.assertFalse(self.memory.has_asked_in_previous_session("Will I pass my exam?"))
        self.assertEqual(self.memory.previous_session_question_count, 0)

    def test_new_question_in_existing_save_is_not_a_prior_session_question(self):
        self.ask("An old question?")
        self.memory.save_memory()
        self.memory = Memory(self.path)
        for _ in range(2):
            self.assertNotIn("Déjà Vu", self.ask("A new question?"))
        self.assertEqual(self.memory.previous_session_question_count, 1)

    def test_secrets_are_anonymous_when_locked_and_revealed_when_unlocked(self):
        output = self.capture(show_achievements, self.memory, self.tracker)
        self.assertEqual(output.count("[Locked] ???"), 6)
        for name in self.tracker.secret_achievements:
            self.assertNotIn(name, output)
            self.assertNotIn(self.tracker.descriptions[name], output)
        self.memory.achievements.add("Night Owl")
        output = self.capture(show_achievements, self.memory, self.tracker)
        self.assertIn("[Unlocked] Night Owl: Consulted the Oracle in the dead of night.", output)
        self.assertEqual(output.count("[Locked] ???"), 5)
        self.assertEqual(self.tracker.get_normal_achievement_count(), 4)

    def test_help_stats_and_readme_do_not_spoil_secrets(self):
        output = self.capture(show_help) + self.capture(show_stats, self.memory, "sage", self.tracker)
        output += Path(main.__file__).with_name("README.md").read_text(encoding="utf-8")
        for name in self.tracker.secret_achievements:
            self.assertNotIn(name, output)
            self.assertNotIn(self.tracker.descriptions[name], output)
        for phrase in TRIGGERS:
            self.assertNotIn(phrase, output.casefold())

    def test_each_required_easter_egg_phrase_matches(self):
        for phrase in (
            "Are you real?", "Are you alive?", "Who created you?",
            "What is the meaning of life?", "Can you see the future?",
            "Do you know the future?", "Are you self-aware?",
        ):
            self.assertIsNotNone(get_easter_egg_response(phrase, "sage"))

    def test_easter_egg_matching_tolerates_case_space_and_terminal_punctuation(self):
        for phrase in TRIGGERS:
            expected = get_easter_egg_response(phrase, "sage")
            for punctuation in ("", "?", ".", "!", "?!", "..."):
                question = "  " + phrase.upper().replace(" ", "  ") + punctuation + " \n"
                self.assertEqual(get_easter_egg_response(question, "sage"), expected)

    def test_unrelated_questions_do_not_trigger_easter_eggs(self):
        for question in (
            "Do you think real estate prices will fall?", "Are you really there?",
            "Are you real or imaginary?", "Please tell me who created you",
            "Can you see the future of my job?", "Are you self-aware of my exams?",
            "help", "", "Who? created you?",
        ):
            self.assertIsNone(get_easter_egg_response(question, "sage"))

    def test_easter_egg_personality_flavor_for_every_phrase(self):
        for phrase in TRIGGERS:
            responses = {get_easter_egg_response(phrase, personality) for personality in PERSONALITY_NAMES}
            self.assertEqual(len(responses), 7)
            self.assertTrue(all(response and response.strip() for response in responses))

    def test_easter_eggs_save_real_questions_and_skip_events_awareness_and_answers(self):
        for phrase in TRIGGERS:
            self.path.unlink(missing_ok=True)
            output, clock, events, awareness, answer = self.play(["1", phrase + "?", "quit"], hour=3)
            self.assertIn(get_easter_egg_response(phrase, "sage"), output)
            self.assertNotIn("NORMAL ANSWER", output)
            for mock in (events, awareness, answer):
                mock.assert_not_called()
            clock.assert_called_once_with()
            restored = Memory(self.path)
            self.assertEqual(restored.questions_asked, 1)
            self.assertEqual(restored.question_history, [phrase + "?"])
            self.assertEqual(restored.repeat_count, {phrase + "?": 1})
            self.assertEqual(restored.achievements, {"First Question", "Night Owl"})
            self.assertEqual(restored.used_personalities, {"sage"})

    def test_easter_egg_repetition_unlocks_achievements_across_sessions(self):
        self.play(["1"] + ["Are you real?"] * 9 + ["quit"])
        output, *_ = self.play(["2", "ARE YOU REAL?", "quit"])
        restored = Memory(self.path)
        self.assertEqual(restored.questions_asked, 10)
        self.assertEqual(restored.repeat_count, {"are you real?": 10})
        self.assertIn("Indecisive UNLOCKED!", output)
        self.assertIn("Déjà Vu UNLOCKED!", output)
        self.assertIn(get_easter_egg_response("Are you real?", "student"), output)

    def test_secret_displays_and_easter_egg_lookup_do_not_mutate_progress(self):
        self.ask()
        state = copy.deepcopy(vars(self.memory))
        self.capture(show_achievements, self.memory, self.tracker)
        get_easter_egg_response("Are you alive?", "robot")
        self.assertEqual(vars(self.memory), state)


if __name__ == "__main__":
    unittest.main()
