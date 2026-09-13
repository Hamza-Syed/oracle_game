"""Tkinter frontend for the shared engine. Run with: python gui.py."""

import tkinter as tk
from tkinter import messagebox

from game import OracleGame


BG = "#10101c"
PANEL = "#1a1a2b"
TEXT = "#eeeaf6"
MUTED = "#b0a9c6"
GOLD = "#ddbf7f"
PURPLE = "#b8a0ec"
BORDER = "#49405e"
WARNING = "#ffd0ab"
BLUE = "#a8c8ed"
BALL_DARK = "#080913"
BALL_LIGHT = "#282539"
WINDOW = "#d8d3e6"
BANNER = "#302a20"
ACTIVE = "#35304c"
ACTIVE_GOLD = "#ead5a8"
DISABLED = "#706c80"
SHAKE_OFFSETS = (0, -4, 4, -3, 3, -2, 2, -1, 1, 0)
STEP_MS = 90
BANNER_MS = 5000
PERSONALITY_ACCENTS = {
    "sage": ("✦", GOLD), "student": ("?", PURPLE), "pirate": ("⚓", GOLD),
    "fortune_teller": ("◇", PURPLE), "wizard": ("✧", PURPLE),
    "alien": ("◎", BLUE), "robot": ("+", BLUE),
}


def personality_accent(personality_id):
    return PERSONALITY_ACCENTS.get(personality_id, ("✦", GOLD))


def information_lines(kind, data):
    """Prepare display lines from public engine snapshots, never from a save."""
    if kind == "stats":
        labels = {
            "questions_asked": "Lifetime questions", "unique_questions": "Unique questions",
            "repeated_questions": "Repeated questions", "personality_name": "Current personality",
            "achievements_unlocked": "Achievements unlocked", "normal_achievements": "Known non-secret achievements",
            "awareness_stage": "Awareness stage", "favorite_topic": "Favorite topic",
        }
        return [f"{label}: {data.get(key, '—')}" for key, label in labels.items()]
    if kind == "history":
        return [f"{entry['number']}. {entry['question']}" for entry in data] or [
            "You haven't asked any questions yet. Ask away, seeker!"
        ]
    if kind == "help":
        return [f"{name}: {description}" for name, description in data.items()]
    if kind == "achievements":
        lines = []
        for entry in data:
            if entry["name"] is None:
                lines.append("[Locked] ???")
            else:
                status = "Unlocked" if entry["unlocked"] else "Locked"
                lines.append(f"[{status}] {entry['name']}\n{entry['description']}")
        return lines
    return []


class OracleGUI:
    def __init__(self, root, game=None):
        self.root = root
        self.game = game if game is not None else OracleGame()
        self.busy = False
        self.closed = False
        self.selection_window = None
        self.finish_callback = None
        self.ball_state = "8"
        self.shake_offset = 0
        self.presentation_id = 0
        self.animation_callback = None
        self.pending_result = None
        self.banner_callback = None
        self.banner_id = 0
        self.information_windows = {}
        self.root.title("The Oracle")
        self.root.geometry("900x780")
        self.root.minsize(740, 700)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.handle_close)
        self.build_ui()
        self.update_personality()
        self.show_personality_selector()

    def button(self, parent, text, command, primary=False):
        return tk.Button(
            parent, text=text, command=command, font=("Segoe UI", 10, "bold"),
            bg=GOLD if primary else PANEL, fg=BG if primary else TEXT,
            activebackground=ACTIVE_GOLD if primary else ACTIVE, activeforeground=BG if primary else TEXT,
            relief="flat", borderwidth=0, padx=14, pady=10, cursor="hand2",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=GOLD,
            disabledforeground=DISABLED,
        )

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame = tk.Frame(self.root, bg=BG, padx=28, pady=20)
        frame.grid(sticky="nsew")
        frame.columnconfigure(0, weight=1)
        # Protect readable text when banners or desktop scaling need more room.
        # The Canvas can yield space; extra window height favors the response.
        frame.rowconfigure(2, weight=1, minsize=100)
        frame.rowconfigure(4, weight=3, minsize=150)
        tk.Label(frame, text="THE ORACLE", font=("Georgia", 28), fg=GOLD, bg=BG).grid(row=0)
        self.personality_label = tk.Label(frame, font=("Segoe UI", 12, "bold"), fg=GOLD, bg=BG)
        self.personality_label.grid(row=1, pady=(4, 0))
        self.canvas = tk.Canvas(frame, height=240, bg=BG, highlightthickness=0)
        self.canvas.grid(row=2, sticky="nsew", pady=6)
        self.canvas.bind("<Configure>", self.draw_oracle)
        self.response_title = tk.Label(frame, text="A question opens a possibility.",
                                       font=("Segoe UI", 12, "bold"), fg=PURPLE, bg=BG)
        self.response_title.grid(row=3, sticky="w", pady=(4, 8))
        self.response = self.make_text_area(frame, row=4, height=6)
        styles = {
            "default": (TEXT, 12), "answer": (TEXT, 14), "topic": (MUTED, 11),
            "repeat_notice": (MUTED, 11), "repeat": (MUTED, 11),
            "achievement": (GOLD, 12), "event": (PURPLE, 13), "awareness": (BLUE, 12),
            "easter_egg": (PURPLE, 14), "safety": (TEXT, 13), "error": (WARNING, 12),
            "notice": (TEXT, 12),
        }
        for role, (color, size) in styles.items():
            self.response.tag_configure(role, foreground=color, font=("Segoe UI", size), spacing3=10)
        self.response.tag_configure("awareness", font=("Segoe UI", 12, "italic"), spacing1=5)
        self.notification = tk.Label(frame, text="", fg=GOLD, bg=BG,
                                     font=("Segoe UI", 11, "bold"), justify="left", anchor="w", wraplength=650)
        self.notification.grid(row=5, sticky="ew", pady=(5, 0))
        self.save_status = tk.Label(frame, text="", fg=WARNING, bg=BG,
                                    font=("Segoe UI", 10), anchor="w", justify="left", wraplength=650)
        self.save_status.grid(row=6, sticky="ew")
        frame.bind("<Configure>", lambda event: [label.configure(wraplength=max(260, event.width - 70))
                                                for label in (self.notification, self.save_status)])
        question_row = tk.Frame(frame, bg=BG)
        question_row.grid(row=7, sticky="ew", pady=(12, 8))
        question_row.columnconfigure(0, weight=1)
        tk.Label(question_row, text="YOUR QUESTION", font=("Segoe UI", 9, "bold"),
                 fg=MUTED, bg=BG).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.entry = tk.Entry(question_row, font=("Segoe UI", 13), bg=PANEL, fg=TEXT,
                              insertbackground=GOLD, relief="flat", highlightthickness=1,
                              highlightbackground=BORDER, highlightcolor=GOLD,
                              disabledbackground=PANEL, disabledforeground=MUTED)
        self.entry.grid(row=1, column=0, sticky="ew", ipady=10, padx=(0, 10))
        self.entry.bind("<Return>", self.submit_question)
        self.ask_button = self.button(question_row, "Ask the Oracle", self.submit_question, primary=True)
        self.ask_button.grid(row=1, column=1)
        toolbar = tk.Frame(frame, bg=BG)
        toolbar.grid(row=8, sticky="ew", pady=(4, 0))
        for column, (label, callback) in enumerate((
            ("Change Personality", self.show_personality_selector), ("Stats", self.show_stats),
            ("Achievements", self.show_achievements), ("History", self.show_history), ("Help", self.show_help),
        )):
            toolbar.columnconfigure(column, weight=1)
            self.button(toolbar, label, callback).grid(row=0, column=column, sticky="ew", padx=3)
        self.set_question_controls()

    def make_text_area(self, parent, row=0, height=12):
        frame = tk.Frame(parent, bg=PANEL)
        frame.grid(row=row, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        text = tk.Text(frame, wrap="word", height=height, width=1, bg=PANEL, fg=TEXT,
                       font=("Segoe UI", 12), relief="flat", padx=16, pady=12,
                       state="disabled", undo=False, exportselection=False)
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(frame, command=text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scrollbar.set)
        return text

    def draw_oracle(self, event=None):
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if min(width, height) < 30:
            return
        x = width / 2 + self.shake_offset
        y = height / 2
        radius = min(height / 2 - 12, width / 2 - 16, 108)
        symbol, accent = personality_accent(self.game.personality)
        canvas.create_oval(x-radius-8, y-radius-8, x+radius+8, y+radius+8, outline=BORDER)
        for scale, color in ((1, BALL_DARK), (.96, PANEL), (.87, BALL_LIGHT), (.75, PANEL)):
            r = radius * scale
            canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline="")
        canvas.create_arc(x-radius+14, y-radius+14, x+radius-14, y+radius-14,
                          start=40, extent=100, style="arc", outline=PURPLE, width=2)
        r = radius * .49
        idle = self.ball_state == "8"
        canvas.create_oval(x-r, y-r, x+r, y+r, fill=WINDOW if idle else BALL_DARK, outline=accent, width=2)
        if not idle:
            canvas.create_polygon(x, y-r*.76, x-r*.76, y+r*.5, x+r*.76, y+r*.5,
                                  fill=ACTIVE, outline=accent)
        canvas.create_text(x, y, text=self.ball_state, fill=PANEL if idle else TEXT,
                           font=("Georgia", int(radius * (.46 if idle else .25))))
        canvas.create_text(x, y+radius*.77, text=symbol, fill=accent, font=("Segoe UI", 12))

    def update_personality(self):
        name = self.game.get_stats()["personality_name"]
        symbol, accent = personality_accent(self.game.personality)
        self.personality_label.configure(text=f"{symbol}  Current Oracle: {name}" if name else "Choose a voice for your Oracle", fg=accent)
        self.draw_oracle()
        self.set_question_controls()

    def set_question_controls(self):
        state = "normal" if self.game.personality is not None and not self.busy else "disabled"
        self.entry.configure(state=state)
        self.ask_button.configure(state=state)

    def show_personality_selector(self):
        if self.closed or self.pending_result is not None:
            return
        if self.selection_window is not None and self.selection_window.winfo_exists():
            self.selection_window.lift()
            return
        window = tk.Toplevel(self.root)
        self.selection_window = window
        window.title("Choose your Oracle")
        window.configure(bg=BG, padx=24, pady=20)
        window.transient(self.root)
        window.columnconfigure(0, weight=1)
        tk.Label(window, text="Choose your Oracle", font=("Georgia", 20), bg=BG, fg=GOLD).grid(pady=(0, 12))
        for row, (key, name) in enumerate(self.game.get_personalities().items(), 1):
            self.button(window, name, lambda selected=key: self.select_personality(selected)).grid(
                row=row, sticky="ew", pady=3,
            )
        window.bind("<Escape>", lambda event: window.destroy())
        window.grab_set()
        window.focus_set()

    def select_personality(self, personality_id):
        if self.closed or self.pending_result is not None:
            return
        result = self.game.select_personality(personality_id)
        self.render_result(result)
        if result.kind == "personality_selected":
            if self.selection_window is not None:
                self.selection_window.destroy()
                self.selection_window = None
            self.update_personality()
            self.entry.focus_set()

    def submit_question(self, event=None):
        if self.closed or self.busy or self.game.personality is None:
            return "break"
        self.busy = True
        text = self.entry.get()
        self.set_question_controls()
        try:
            result = self.game.process_input(text)
            # Clear even safety input; never keep a GUI question log or undo stack.
            self.entry.configure(state="normal")
            self.entry.delete(0, "end")
            self.entry.configure(state="disabled")
            if result.kind in {"question", "event", "easter_egg", "self_evaluation", "preference"}:
                self.start_consultation(result)
            else:
                self.render_result(result)
        finally:
            if not self.closed and self.pending_result is None:
                token = self.presentation_id
                self.finish_callback = self.root.after_idle(lambda: self.finish_submission(token))
        return "break"

    def finish_submission(self, token=None):
        if self.closed or (token is not None and token != self.presentation_id):
            return
        self.finish_callback = None
        self.busy = False
        if not self.closed:
            self.set_question_controls()
            if self.selection_window is None or not self.selection_window.winfo_exists():
                self.entry.focus_set()

    def cancel_consultation(self):
        self.presentation_id += 1
        for name in ("animation_callback", "finish_callback"):
            callback = getattr(self, name)
            if callback is not None:
                self.root.after_cancel(callback)
                setattr(self, name, None)
        self.pending_result = None
        self.shake_offset = 0

    def start_consultation(self, result):
        self.cancel_consultation()
        self.hide_banner()
        self.pending_result = result
        self.busy = True
        self.set_question_controls()
        self.ball_state = "..."
        self.canvas.grid()
        self.response_title.configure(text="Consulting the Oracle...", fg=PURPLE)
        self.response.configure(state="normal")
        self.response.delete("1.0", "end")
        self.response.configure(state="disabled")
        self.animate_consultation(self.presentation_id, 0)

    def animate_consultation(self, token, step):
        if self.closed or token != self.presentation_id or self.pending_result is None:
            return
        self.animation_callback = None
        if step == len(SHAKE_OFFSETS):
            result = self.pending_result
            self.pending_result = None
            self.shake_offset = 0
            self.render_result(result)
            self.finish_submission()
            return
        self.shake_offset = SHAKE_OFFSETS[step]
        self.draw_oracle()
        self.animation_callback = self.root.after(
            STEP_MS, lambda: self.animate_consultation(token, step + 1),
        )

    def hide_banner(self):
        self.banner_id += 1
        if self.banner_callback is not None:
            self.root.after_cancel(self.banner_callback)
            self.banner_callback = None
        self.notification.configure(text="", bg=BG, padx=0, pady=0)

    def show_achievement_banner(self, names):
        self.hide_banner()
        if not names:
            return
        self.notification.configure(text="🏆 Achievement Unlocked\n" + " · ".join(names),
                                    bg=BANNER, padx=12, pady=8)
        token = self.banner_id
        def dismiss():
            if not self.closed and token == self.banner_id:
                self.banner_callback = None
                self.hide_banner()
        self.banner_callback = self.root.after(BANNER_MS, dismiss)

    def render_result(self, result):
        if self.closed:
            return
        if result.kind == "quit":
            self.handle_close()
            return
        if result.kind == "select_personality":
            self.show_personality_selector()
            return
        if result.kind in {"stats", "history", "achievements", "help"}:
            self.show_information(result.kind, result.data)
            return
        if result.kind in {"follow_up", "conversation", "vulgar_reaction"}:
            self.canvas.grid()
            self.response_title.configure(text="The Oracle says", fg=PURPLE)
            self.display_messages(result)
            return
        self.cancel_consultation()
        if result.save_error is not None:
            self.save_status.configure(text="Your action was processed, but progress could not be saved.\n" + result.save_error)
        elif result.kind in {"question", "event", "easter_egg", "self_evaluation", "preference"} or result.new_achievements:
            self.save_status.configure(text="")
        if not result.messages:
            return
        safety = result.kind == "safety"
        if safety:
            self.canvas.grid_remove()
            self.response_title.configure(text="Support and safety", fg=TEXT)
            self.hide_banner()
            self.finish_submission()
        else:
            self.canvas.grid()
            if result.kind in {"question", "event", "easter_egg", "self_evaluation", "preference"}:
                self.ball_state = "◇" if result.kind == "event" else "✦"
                self.draw_oracle()
            self.response_title.configure(text="An unusual response" if result.kind == "event" else "The Oracle says", fg=PURPLE)
            self.show_achievement_banner(result.new_achievements)
        self.display_messages(result, safety=safety)

    def display_messages(self, result, safety=False):
        self.response.configure(state="normal")
        self.response.delete("1.0", "end")
        for message in result.messages:
            role = "safety" if safety else message.role
            tag = role if role in self.response.tag_names() else "default"
            text = message.text
            if role == "achievement":
                text = "Achievement Unlocked: " + text
            self.response.insert("end", text + "\n\n", tag)
        self.response.configure(state="disabled")
        self.response.yview_moveto(0)

    def show_information(self, kind, data):
        if self.closed:
            return
        existing = self.information_windows.get(kind)
        if existing is not None and existing[0].winfo_exists():
            window, text = existing
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("end", "\n\n".join(information_lines(kind, data)))
            text.configure(state="disabled")
            window.lift()
            window.focus_set()
            return
        window = tk.Toplevel(self.root)
        window.title("The Oracle · " + kind.title())
        window.geometry("560x460")
        window.minsize(360, 280)
        window.configure(bg=BG, padx=18, pady=18)
        window.transient(self.root)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        title = "Recent history · oldest to newest" if kind == "history" else kind.title()
        tk.Label(window, text=title, font=("Georgia", 18), bg=BG, fg=GOLD).grid(sticky="w", pady=(0, 12))
        text = self.make_text_area(window, row=1)
        self.information_windows[kind] = (window, text)
        text.configure(state="normal")
        text.insert("end", "\n\n".join(information_lines(kind, data)))
        text.configure(state="disabled")
        window.bind("<Escape>", lambda event: window.destroy())

    def show_stats(self):
        self.show_information("stats", self.game.get_stats())

    def show_history(self):
        self.show_information("history", self.game.get_history())

    def show_achievements(self):
        self.show_information("achievements", self.game.get_achievements())

    def show_help(self):
        self.show_information("help", self.game.get_help())

    def handle_close(self):
        if self.closed:
            return
        self.closed = True
        self.cancel_consultation()
        self.hide_banner()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        OracleGUI(root)
    except (OSError, ValueError) as error:
        messagebox.showerror("Could not load memory", str(error) + "\nYour save has not been changed.", parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
