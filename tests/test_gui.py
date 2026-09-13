"""Thin frontend tests using widget doubles; no display server is required."""

from unittest import TestCase
from unittest.mock import Mock, patch

from game import GameResult, Message
from gui import OracleGUI, information_lines, personality_accent, SHAKE_OFFSETS


class GUITests(TestCase):
    def setUp(self):
        self.app = OracleGUI.__new__(OracleGUI)
        self.app.root = Mock()
        self.app.game = Mock()
        self.app.game.personality = "sage"
        self.app.closed = False
        self.app.busy = False
        self.app.finish_callback = None
        self.app.selection_window = None
        self.app.ball_state = "8"
        self.app.shake_offset = 0
        self.app.presentation_id = 0
        self.app.animation_callback = None
        self.app.pending_result = None
        self.app.banner_callback = None
        self.app.banner_id = 0
        self.app.information_windows = {}
        self.app.draw_oracle = Mock()
        for name in ("entry", "ask_button", "response", "response_title", "canvas",
                     "notification", "save_status", "personality_label"):
            setattr(self.app, name, Mock())
        self.app.response.tag_names.return_value = (
            "default", "answer", "topic", "repeat", "achievement", "safety", "error", "event",
        )

    def test_personality_selector_uses_engine_ids_and_names(self):
        self.app.game.get_personalities.return_value = {"new_id": "New Oracle", "sage": "Wise Sage"}
        self.app.button = Mock()
        self.app.select_personality = Mock()
        with patch("gui.tk.Toplevel"), patch("gui.tk.Label"):
            self.app.show_personality_selector()
        calls = self.app.button.call_args_list
        self.assertEqual([call.args[1] for call in calls], ["New Oracle", "Wise Sage"])
        calls[0].args[2]()
        self.app.select_personality.assert_called_once_with("new_id")

    def test_selection_delegates_and_enables_controls(self):
        self.app.game.select_personality.return_value = GameResult("personality_selected")
        self.app.selection_window = Mock()
        self.app.game.get_stats.return_value = {"personality_name": "Wise Sage"}
        self.app.select_personality("sage")
        self.app.game.select_personality.assert_called_once_with("sage")
        self.app.ask_button.configure.assert_called_with(state="normal")
        self.assertIsNone(self.app.selection_window)

    def test_invalid_selection_keeps_selector_open(self):
        self.app.selection_window = Mock()
        self.app.game.select_personality.return_value = GameResult(
            "invalid_selection", [Message("notice", "Invalid personality selection.")],
        )
        self.app.select_personality("missing")
        self.app.selection_window.destroy.assert_not_called()

    def test_submit_calls_engine_once_with_original_text_and_clears_entry(self):
        self.app.entry.get.return_value = "  A question?  "
        result = GameResult("question", [Message("answer", "An answer.")])
        self.app.game.process_input.return_value = result
        self.app.render_result = Mock()
        self.assertEqual(self.app.submit_question(), "break")
        self.app.submit_question()  # Queued click/Enter before the idle callback.
        self.app.game.process_input.assert_called_once_with("  A question?  ")
        self.app.entry.delete.assert_called_once_with(0, "end")
        self.app.render_result.assert_not_called()
        self.app.animate_consultation(self.app.presentation_id, len(SHAKE_OFFSETS))
        self.app.render_result.assert_called_once_with(result)
        self.app.finish_submission()
        self.assertFalse(self.app.busy)

    def test_no_submission_before_selection_and_blank_goes_to_engine(self):
        self.app.game.personality = None
        self.app.submit_question()
        self.app.game.process_input.assert_not_called()
        self.app.game.personality = "sage"
        self.app.entry.get.return_value = " \t "
        self.app.game.process_input.return_value = GameResult("blank")
        self.app.submit_question()
        self.app.game.process_input.assert_called_once_with(" \t ")

    def test_finish_submission_does_not_steal_personality_dialog_focus(self):
        self.app.selection_window = Mock()
        self.app.selection_window.winfo_exists.return_value = True
        self.app.finish_submission()
        self.app.entry.focus_set.assert_not_called()

    def test_submitted_quit_does_not_schedule_callback_after_destroy(self):
        self.app.entry.get.return_value = "quit"
        self.app.game.process_input.return_value = GameResult("quit")
        self.app.submit_question()
        self.app.root.destroy.assert_called_once()
        self.app.root.after_idle.assert_not_called()

    def test_message_order_and_unknown_role_fallback(self):
        self.app.draw_oracle = Mock()
        result = GameResult("question", [
            Message("topic", "Topic"), Message("repeat", "Repeat"),
            Message("achievement", "First Question"), Message("future_role", "Unknown"),
            Message("answer", "Answer"),
        ], new_achievements=["First Question"])
        self.app.render_result(result)
        calls = self.app.response.insert.call_args_list
        self.assertEqual([call.args[1] for call in calls], [
            "Topic\n\n", "Repeat\n\n", "Achievement Unlocked: First Question\n\n", "Unknown\n\n", "Answer\n\n",
        ])
        self.assertEqual(calls[3].args[2], "default")
        self.assertIn("First Question", self.app.notification.configure.call_args.kwargs["text"])

    def test_safety_preserves_exact_wording_hides_ball_and_uses_plain_style(self):
        self.app.draw_oracle = Mock()
        wording = "Plain support information.\nA longer line with contact details."
        self.app.render_result(GameResult("safety", [Message("safety", wording)]))
        self.app.response.insert.assert_called_once_with("end", wording + "\n\n", "safety")
        self.app.canvas.grid_remove.assert_called_once()
        self.app.draw_oracle.assert_not_called()
        self.assertEqual(self.app.notification.configure.call_args.kwargs["text"], "")
        self.app.response.yview_moveto.assert_called_once_with(0)

    def test_save_error_keeps_answer_and_displays_error(self):
        self.app.draw_oracle = Mock()
        self.app.render_result(GameResult("question", [Message("answer", "Answer")], save_error="Disk full"))
        self.assertIn("Disk full", self.app.save_status.configure.call_args.kwargs["text"])
        self.app.response.insert.assert_called_once_with("end", "Answer\n\n", "answer")

    def test_typed_quit_destroys_window_without_another_engine_call(self):
        self.app.render_result(GameResult("quit"))
        self.app.root.destroy.assert_called_once()
        self.app.game.process_input.assert_not_called()
        self.assertTrue(self.app.closed)

    def test_close_cancels_pending_callback_and_is_idempotent(self):
        self.app.finish_callback = "after#1"
        self.app.handle_close()
        self.app.handle_close()
        self.app.root.after_cancel.assert_called_once_with("after#1")
        self.app.root.destroy.assert_called_once()
        self.app.game.process_input.assert_not_called()

    def test_information_buttons_use_direct_engine_getters(self):
        self.app.show_information = Mock()
        for kind in ("stats", "history", "achievements", "help"):
            data = object()
            getattr(self.app.game, "get_" + kind).return_value = data
            getattr(self.app, "show_" + kind)()
            getattr(self.app.game, "get_" + kind).assert_called_once_with()
            self.app.show_information.assert_called_with(kind, data)
        self.app.game.process_input.assert_not_called()

    def test_typed_commands_use_result_snapshots_and_change_opens_selector(self):
        self.app.show_information = Mock()
        self.app.show_personality_selector = Mock()
        for kind in ("stats", "history", "achievements", "help"):
            self.app.render_result(GameResult(kind, data={"snapshot": True}))
            self.app.show_information.assert_called_with(kind, {"snapshot": True})
        self.app.render_result(GameResult("select_personality"))
        self.app.show_personality_selector.assert_called_once_with()

    def test_achievement_display_does_not_expose_locked_secret_metadata(self):
        entries = [
            {"name": "First Question", "description": "Ask once", "unlocked": True},
            {"name": "Oracle Addict", "description": "Ask more", "unlocked": False},
            {"name": None, "description": "Must not be shown", "unlocked": False},
        ]
        lines = information_lines("achievements", entries)
        self.assertEqual(lines, ["[Unlocked] First Question\nAsk once", "[Locked] Oracle Addict\nAsk more", "[Locked] ???"])

    def test_history_help_and_stats_format_engine_values(self):
        self.assertEqual(information_lines("history", [{"number": 3, "question": "Original question?"}]),
                         ["3. Original question?"])
        self.assertIn("haven't asked", information_lines("history", [])[0])
        self.assertEqual(information_lines("help", {"help": "Show help"}), ["help: Show help"])
        self.assertIn("Lifetime questions: 37", information_lines("stats", {"questions_asked": 37}))

    def test_startup_load_failure_is_a_dialog_and_clean_exit(self):
        from gui import main
        with patch("gui.tk.Tk") as root, \
                patch("gui.OracleGUI", side_effect=OSError("Save unavailable")), \
                patch("gui.messagebox.showerror") as error:
            main()
        self.assertIn("Save unavailable", error.call_args.args[1])
        root.return_value.destroy.assert_called_once()
        root.return_value.mainloop.assert_not_called()

    def test_consultation_disables_controls_then_reveals_in_order_and_restores_focus(self):
        result = GameResult("question", [Message("topic", "First"), Message("answer", "Second")])
        self.app.start_consultation(result)
        self.assertTrue(self.app.busy)
        self.app.ask_button.configure.assert_called_with(state="disabled")
        self.app.response.insert.assert_not_called()
        token = self.app.presentation_id
        for step in range(1, len(SHAKE_OFFSETS) + 1):
            self.app.animate_consultation(token, step)
        self.assertEqual(self.app.shake_offset, 0)
        self.assertFalse(self.app.busy)
        self.app.ask_button.configure.assert_called_with(state="normal")
        self.app.entry.focus_set.assert_called_once()
        self.assertEqual([call.args[1] for call in self.app.response.insert.call_args_list], ["First\n\n", "Second\n\n"])

    def test_safety_submission_skips_consultation(self):
        self.app.game.process_input.return_value = GameResult("safety", [Message("safety", "Support")])
        self.app.start_consultation = Mock()
        self.app.submit_question()
        self.app.start_consultation.assert_not_called()
        self.app.response.insert.assert_called_once_with("end", "Support\n\n", "safety")
        self.assertFalse(self.app.busy)

    def test_conversation_is_immediate_with_one_engine_call_and_no_animation(self):
        self.app.entry.get.return_value = "OK!"
        self.app.game.process_input.return_value = GameResult("conversation", [Message("notice", "Ready when you are.")])
        self.app.start_consultation = Mock()
        self.app.submit_question()
        self.app.game.process_input.assert_called_once_with("OK!")
        self.app.start_consultation.assert_not_called()
        self.app.draw_oracle.assert_not_called()
        self.app.canvas.grid_remove.assert_not_called()
        self.app.canvas.grid.assert_called_once()
        self.app.response.insert.assert_called_once_with("end", "Ready when you are.\n\n", "default")
        self.app.root.after_idle.call_args.args[0]()
        self.app.entry.focus_set.assert_called_once()
        self.assertFalse(self.app.busy)

    def test_follow_up_is_immediate_and_preserves_banner_and_visual_state(self):
        self.app.entry.get.return_value = "Really?"
        self.app.game.process_input.return_value = GameResult("follow_up", [Message("notice", "A reply, not a guarantee.")])
        self.app.banner_callback = "banner#1"
        self.app.start_consultation = Mock()
        token = self.app.presentation_id
        self.app.submit_question()
        self.app.game.process_input.assert_called_once_with("Really?")
        self.app.start_consultation.assert_not_called()
        self.app.draw_oracle.assert_not_called()
        self.app.notification.configure.assert_not_called()
        self.assertEqual(self.app.banner_callback, "banner#1")
        self.assertEqual(self.app.presentation_id, token)
        self.app.canvas.grid_remove.assert_not_called()
        self.app.response.insert.assert_called_once_with("end", "A reply, not a guarantee.\n\n", "default")
        self.app.root.after_idle.call_args.args[0]()
        self.app.entry.focus_set.assert_called_once()

    def test_vulgar_reaction_is_immediate_and_preserves_banner_and_focus(self):
        self.app.entry.get.return_value = "FUCK!"
        self.app.game.process_input.return_value = GameResult("vulgar_reaction", [Message("notice", "Strong words. The stars remain remarkably calm.")])
        self.app.banner_callback = "banner#1"
        self.app.start_consultation = Mock()
        token = self.app.presentation_id
        self.app.submit_question()
        self.app.game.process_input.assert_called_once_with("FUCK!")
        self.app.start_consultation.assert_not_called()
        self.app.draw_oracle.assert_not_called()
        self.app.notification.configure.assert_not_called()
        self.app.root.after_cancel.assert_not_called()
        self.assertEqual(self.app.banner_callback, "banner#1")
        self.assertEqual(self.app.presentation_id, token)
        self.app.canvas.grid_remove.assert_not_called()
        self.app.response.insert.assert_called_once_with("end", "Strong words. The stars remain remarkably calm.\n\n", "default")
        self.app.root.after_idle.call_args.args[0]()
        self.app.entry.focus_set.assert_called_once()
        self.assertFalse(self.app.busy)

    def test_acknowledgments_preserve_banner_and_timer_without_animation(self):
        self.app.banner_callback = "banner#1"
        self.app.start_consultation = Mock()
        for phrase in ("I see", "I SEE.", "Gotcha!", "Fair enough.", "Makes sense", "Understood!"):
            with self.subTest(phrase=phrase):
                self.app.game.process_input.reset_mock()
                self.app.entry.get.return_value = phrase
                self.app.game.process_input.return_value = GameResult("conversation", [Message("notice", "Ready when you are.")])
                self.app.submit_question()
                self.app.game.process_input.assert_called_once_with(phrase)
                self.app.start_consultation.assert_not_called()
                self.app.draw_oracle.assert_not_called()
                self.app.notification.configure.assert_not_called()
                self.app.root.after_cancel.assert_not_called()
                self.assertEqual(self.app.banner_callback, "banner#1")
                self.app.canvas.grid_remove.assert_not_called()
                self.app.response.insert.assert_called_with("end", "Ready when you are.\n\n", "default")
                self.app.root.after_idle.call_args.args[0]()
                self.assertFalse(self.app.busy)
        self.assertEqual(self.app.entry.focus_set.call_count, 6)

    def test_self_evaluation_uses_consultation_animation_and_regular_answer_style(self):
        self.app.entry.get.return_value = "Am I smart?"
        self.app.game.process_input.return_value = GameResult("self_evaluation", [Message("answer", "Reflective reply")])
        self.app.submit_question()
        self.app.game.process_input.assert_called_once_with("Am I smart?")
        self.assertTrue(self.app.busy)
        self.app.response.insert.assert_not_called()
        self.app.animate_consultation(self.app.presentation_id, len(SHAKE_OFFSETS))
        self.app.response.insert.assert_called_once_with("end", "Reflective reply\n\n", "answer")
        self.app.canvas.grid_remove.assert_not_called()
        self.assertFalse(self.app.busy)

    def test_preference_uses_existing_reveal_while_acknowledgment_is_immediate(self):
        self.app.entry.get.return_value = "Do you like water?"
        self.app.game.process_input.return_value = GameResult("preference", [Message("answer", "Banter")])
        self.app.submit_question()
        self.assertTrue(self.app.busy)
        self.app.response.insert.assert_not_called()
        self.app.animate_consultation(self.app.presentation_id, len(SHAKE_OFFSETS))
        self.app.response.insert.assert_called_once_with("end", "Banter\n\n", "answer")
        self.app.canvas.grid_remove.assert_not_called()
        self.app.game.process_input.assert_called_once_with("Do you like water?")
        self.app.entry.get.return_value = "Wonderful!"
        self.app.game.process_input.return_value = GameResult("conversation", [Message("notice", "Ready")])
        self.app.start_consultation = Mock()
        self.app.submit_question()
        self.app.start_consultation.assert_not_called()
        self.app.response.insert.assert_called_with("end", "Ready\n\n", "default")

    def test_safety_cancels_pending_reveal_and_stale_callback_cannot_overwrite(self):
        self.app.start_consultation(GameResult("question", [Message("answer", "Old answer")]))
        old_callback = self.app.root.after.call_args.args[1]
        self.app.render_result(GameResult("safety", [Message("safety", "Support")]))
        old_callback()
        self.assertIsNone(self.app.pending_result)
        self.assertEqual(self.app.shake_offset, 0)
        self.app.response.insert.assert_called_once_with("end", "Support\n\n", "safety")
        self.app.canvas.grid_remove.assert_called_once()

    def test_old_reveal_cannot_replace_new_consultation(self):
        old = GameResult("question", [Message("answer", "Old")])
        new = GameResult("question", [Message("answer", "New")])
        self.app.start_consultation(old)
        token = self.app.presentation_id
        self.app.start_consultation(new)
        self.app.animate_consultation(token, len(SHAKE_OFFSETS))
        self.app.response.insert.assert_not_called()
        self.assertIs(self.app.pending_result, new)

    def test_multiple_achievements_share_one_temporary_banner(self):
        self.app.show_achievement_banner(["First Question", "Persistent Seeker"])
        self.assertEqual(self.app.notification.configure.call_args.kwargs["text"],
                         "🏆 Achievement Unlocked\nFirst Question · Persistent Seeker")
        self.app.root.after.call_args.args[1]()
        self.assertEqual(self.app.notification.configure.call_args.kwargs["text"], "")

    def test_old_banner_callback_cannot_hide_new_banner(self):
        self.app.show_achievement_banner(["First Question"])
        old_dismiss = self.app.root.after.call_args.args[1]
        self.app.show_achievement_banner(["Persistent Seeker"])
        old_dismiss()
        self.assertIn("Persistent Seeker", self.app.notification.configure.call_args.kwargs["text"])

    def test_personality_accents_have_fallback_and_label_updates(self):
        self.assertEqual(personality_accent("unknown"), personality_accent(None))
        self.app.game.get_stats.return_value = {"personality_name": "Pirate"}
        self.app.game.personality = "pirate"
        self.app.update_personality()
        self.assertIn("Current Oracle: Pirate", self.app.personality_label.configure.call_args.kwargs["text"])
        self.assertIn(personality_accent("pirate")[0], self.app.personality_label.configure.call_args.kwargs["text"])

    def test_personality_cannot_change_mid_consultation(self):
        self.app.start_consultation(GameResult("question"))
        with patch("gui.tk.Toplevel") as window:
            self.app.show_personality_selector()
        window.assert_not_called()
        self.app.select_personality("pirate")
        self.app.game.select_personality.assert_not_called()

    def test_quit_during_animation_cancels_all_callbacks(self):
        self.app.start_consultation(GameResult("question", [Message("answer", "Old")]))
        callback = self.app.root.after.call_args.args[1]
        self.app.render_result(GameResult("quit"))
        callback()
        self.app.response.insert.assert_not_called()
        self.app.root.destroy.assert_called_once()
        self.assertIsNone(self.app.pending_result)

    def test_secondary_window_is_reused_with_fresh_data(self):
        window, text = Mock(), Mock()
        window.winfo_exists.return_value = True
        self.app.information_windows["history"] = (window, text)
        with patch("gui.tk.Toplevel") as constructor:
            self.app.show_information("history", [{"number": 2, "question": "New?"}])
        constructor.assert_not_called()
        window.lift.assert_called_once()
        text.insert.assert_called_once_with("end", "2. New?")

    def test_delayed_save_error_does_not_suppress_answer(self):
        self.app.start_consultation(GameResult("question", [Message("answer", "Answer")], save_error="Disk full"))
        self.app.save_status.configure.assert_not_called()
        self.app.animate_consultation(self.app.presentation_id, len(SHAKE_OFFSETS))
        self.assertIn("Disk full", self.app.save_status.configure.call_args.kwargs["text"])
        self.app.response.insert.assert_called_once_with("end", "Answer\n\n", "answer")
