"""Real Tk layout checks, skipped when a graphical display is unavailable."""

from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from game import GameResult, Message, OracleGame
from gui import OracleGUI
from memories import Memory


class GUILayoutTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")
        self.addCleanup(self.root.destroy)
        self.root.withdraw()
        # Invisible, undecorated windows allow geometry checks independent of
        # the test desktop's work-area limit. No mouse interaction is needed.
        self.root.attributes("-alpha", 0)
        self.root.overrideredirect(True)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        with patch.object(OracleGUI, "show_personality_selector"):
            self.app = OracleGUI(self.root, OracleGame(Memory(Path(directory.name) / "memory.json")))
        self.app.select_personality("sage")
        self.root.deiconify()

    def resize(self, geometry):
        self.root.geometry(geometry)
        self.root.update()

    def assert_controls_fit(self):
        bottom = self.root.winfo_rooty() + self.root.winfo_height()
        controls = [self.app.entry, self.app.ask_button]
        layout = self.app.response.master.master
        toolbar = layout.grid_slaves(row=8)[0]
        controls.extend(toolbar.winfo_children())
        for widget in controls:
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), bottom)

    def test_response_has_room_at_default_and_minimum_and_grows_with_window(self):
        self.resize("900x780")
        self.assertGreaterEqual(self.app.response.winfo_height(), 150)
        default_height = self.app.response.winfo_height()
        self.resize("1000x900")
        self.assertGreater(self.app.response.winfo_height(), default_height)
        self.app.show_achievement_banner(["First Question"])
        self.app.save_status.configure(text="Progress could not be saved.\nPlease check the save location.")
        self.resize("740x700")
        self.assertGreaterEqual(self.app.response.winfo_height(), 150)
        self.assert_controls_fit()
        self.app.hide_banner()

    def test_long_styled_and_safety_messages_remain_complete_and_scrollable(self):
        self.resize("900x780")
        for kind, role in (("question", "answer"), ("question", "awareness"),
                           ("event", "event"), ("safety", "safety")):
            with self.subTest(kind=kind):
                content = "Long readable guidance with wrapping. " * 150
                messages = [Message(role, content)]
                if kind != "safety":
                    messages.extend([Message("answer", "A final answer."), Message("error", "Save failed.")])
                self.app.render_result(GameResult(
                    kind, messages, new_achievements=[] if kind == "safety" else ["First Question"],
                    save_error=None if kind == "safety" else "Disk full",
                ))
                self.root.update()
                self.assertEqual(self.app.response.get("1.0", "end-1c"),
                                 "".join(message.text + "\n\n" for message in messages))
                self.assertEqual(self.app.response.cget("wrap"), "word")
                self.assertTrue(self.app.response.tag_ranges(role))
                self.assertLess(self.app.response.yview()[1], 1)
                self.app.response.yview_moveto(1)
                self.assertGreater(self.app.response.yview()[0], 0)
                scrollbar = self.app.response.master.grid_slaves(column=1)[0]
                self.assertTrue(scrollbar.cget("command"))
                self.assert_controls_fit()
        self.assertEqual(self.app.canvas.winfo_manager(), "")

