"""Release integration checks using isolated saves and invisible real Tk widgets."""

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

import game
import main
from game import GameResult, Message, OracleGame
from gui import OracleGUI
from memories import Memory
from personalities import PERSONALITY_NAMES


class ReleaseCandidateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory / "memory.json"
        for target, value in (("game.get_random_event", None), ("game.get_awareness_message", None),
                              ("achievements.get_current_hour", 12)):
            mocked = patch(target, return_value=value)
            mocked.start()
            self.addCleanup(mocked.stop)

    def make_gui(self):
        try:
            root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")
        root.withdraw()
        root.attributes("-alpha", 0)
        errors = []
        root.report_callback_exception = lambda *error: errors.append(error)
        self.addCleanup(lambda: self.assertEqual(errors, []))
        # Hide selectors and information windows as well as the main window.
        real_toplevel = tk.Toplevel
        def invisible_toplevel(*args, **kwargs):
            window = real_toplevel(*args, **kwargs)
            window.attributes("-alpha", 0)
            return window
        windows = patch("gui.tk.Toplevel", side_effect=invisible_toplevel)
        windows.start()
        self.addCleanup(windows.stop)
        app = OracleGUI(root, OracleGame(Memory(self.path)))
        self.addCleanup(lambda: app.handle_close() if not app.closed else None)
        return app

    def pump_until(self, app, condition):
        deadline = time.monotonic() + 8
        while not condition() and time.monotonic() < deadline:
            app.root.update()
            time.sleep(.01)
        self.assertTrue(condition(), "Tk callback did not complete")

    def test_absolute_entry_points_work_from_another_directory(self):
        source = Path(main.__file__).parent
        copied = self.directory / "game"
        copied.mkdir()
        for module in source.glob("*.py"):
            shutil.copy2(module, copied / module.name)
        result = subprocess.run(
            [sys.executable, str(copied / "main.py")], input="1\nWill I succeed?\nquit\n",
            cwd=self.directory, capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("First Question UNLOCKED!", result.stdout)
        self.assertEqual(Memory(copied / "memory.json").questions_asked, 1)
        self.assertFalse(self.path.exists())
        imported = subprocess.run(
            [sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import main, gui", str(copied)],
            cwd=self.directory, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(imported.returncode, 0, imported.stderr)

    def test_fresh_gui_save_terminal_reload_and_gui_restart(self):
        app = self.make_gui()
        choices = [w.cget("text") for w in app.selection_window.winfo_children() if isinstance(w, tk.Button)]
        self.assertEqual(choices, list(PERSONALITY_NAMES.values()))
        app.select_personality("sage")
        self.assertFalse(self.path.exists())
        with patch("game.get_random_event", return_value=None), patch("game.get_awareness_message", return_value=None):
            app.entry.insert(0, "Will I get the job?")
            app.ask_button.invoke()
            app.submit_question()  # A queued second submission must be ignored.
            self.assertTrue(app.busy)
            self.assertEqual(app.game.memory.questions_asked, 1)
            self.pump_until(app, lambda: not app.busy)
        self.assertIn("First Question", app.notification.cget("text"))
        self.assertTrue(app.response.get("1.0", "end-1c"))
        app.handle_close()
        output = io.StringIO()
        inputs = ["3", "Will I get the job?", "nice", "Really?", "damn", "Why?",
                  "Do you like Python?", "Am I smart?", " StAtS ", " HiStOrY ",
                  " AcHiEvEmEnTs ", " HeLp ", " ChAnGe ", "7", " QuIt "]
        with patch.object(game, "Memory", side_effect=lambda: Memory(self.path)), \
                patch("builtins.input", side_effect=inputs), contextlib.redirect_stdout(output):
            main.main()
        self.assertIn("remembers 1 previous questions", output.getvalue())
        self.assertIn("Farewell, seeker.", output.getvalue())
        restarted = OracleGame(Memory(self.path))
        self.assertEqual(restarted.memory.questions_asked, 4)
        self.assertEqual(restarted.memory.repeat_count["will i get the job?"], 2)
        self.assertIsNone(restarted.follow_up_personality)
        self.assertEqual(restarted.last_awareness_messages, {})
        self.assertEqual(restarted.achievement_tracker.personality_changes, 0)
        second = self.make_gui()
        second.select_personality("robot")
        self.assertEqual(second.game.get_stats()["questions_asked"], 4)
        saved = self.path.read_bytes()
        for command in (" HeLp ", " StAtS ", " HiStOrY ", " AcHiEvEmEnTs "):
            for _ in range(2):
                second.entry.insert(0, command)
                second.submit_question()
                second.root.update()
                second.information_windows[command.strip().lower()][0].destroy()
        self.assertEqual(self.path.read_bytes(), saved)
        second.entry.insert(0, " QuIt ")
        second.submit_question()
        self.assertTrue(second.closed)

    def test_real_timers_immediate_replies_banner_expiry_and_close(self):
        app = self.make_gui()
        app.select_personality("sage")
        with patch("game.get_random_event", return_value=None):
            for question in ("Do you like cats?", "Am I smart?"):
                app.entry.insert(0, question)
                app.submit_question()
                self.assertIsNotNone(app.pending_result)
                self.pump_until(app, lambda: not app.busy)
        app.show_achievement_banner(["First Question"])
        callback = app.banner_callback
        saved = self.path.read_bytes()
        for text in ("understood", "Really?", "damn"):
            app.entry.insert(0, text)
            app.submit_question()
            self.assertIsNone(app.pending_result)
            self.assertTrue(app.response.get("1.0", "end-1c"))
            app.root.update()
            self.assertEqual(app.banner_callback, callback)
        self.assertEqual(self.path.read_bytes(), saved)
        self.pump_until(app, lambda: app.banner_callback is None)
        self.assertEqual(app.notification.cget("text"), "")
        app.start_consultation(GameResult("question", [Message("answer", "Pending")]))
        app.handle_close()
        self.assertIsNone(app.animation_callback)
        self.assertIsNone(app.pending_result)
