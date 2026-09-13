"""Achievement rules; unlocked names live in Memory so they can be saved."""

from datetime import datetime

from personalities import PERSONALITY_NAMES


def get_current_hour():
    """Local clock hour, kept separate so tests can replace it."""
    return datetime.now().hour


class AchievementTracker:
    # Names are keys, descriptions are values, and this set marks secret entries.
    secret_achievements = {
        "Night Owl", "Indecisive", "Personality Crisis", "Curious Mortal",
        "Completionist", "Déjà Vu",
    }

    descriptions = {
        "First Question": "Ask your first question.",
        "Persistent Seeker": "Ask 10 questions.",
        "The Doubter": "Ask the same question 5 times.",
        "Oracle Addict": "Ask 100 questions.",
        "Night Owl": "Consulted the Oracle in the dead of night.",
        "Indecisive": "Asked the same question ten times.",
        "Personality Crisis": "Changed personalities five times in one session.",
        "Curious Mortal": "Asked 250 lifetime questions.",
        "Completionist": "Consulted all seven personalities.",
        "Déjà Vu": "Returned to a question from a previous session.",
    }

    def __init__(self):
        self.personality_changes = 0

    def get_normal_achievement_count(self):
        return len(self.descriptions.keys() - self.secret_achievements)

    def get_visible_achievements(self, memory):
        return {
            name: description for name, description in self.descriptions.items()
            if name not in self.secret_achievements or name in memory.achievements
        }

    def check_achievements(self, memory, repeat_number, *, current_hour=None,
                           asked_previous_session=False):
        """Check after a real question; display commands must not call this."""
        if current_hour is None:
            current_hour = get_current_hour()
        highest_repeat = max(memory.repeat_count.values(), default=repeat_number)
        conditions = {
            "First Question": memory.questions_asked >= 1,
            "Persistent Seeker": memory.questions_asked >= 10,
            "The Doubter": highest_repeat >= 5,
            "Oracle Addict": memory.questions_asked >= 100,
            "Night Owl": memory.questions_asked >= 1 and 0 <= current_hour < 5,
            "Indecisive": highest_repeat >= 10,
            "Curious Mortal": memory.questions_asked >= 250,
            "Completionist": set(PERSONALITY_NAMES).issubset(memory.used_personalities),
            "Déjà Vu": asked_previous_session,
        }
        return self.unlock_earned(memory, conditions)

    def record_personality_change(self, memory, previous, selected):
        """Only actual successful switches count, never initial selection or quit."""
        if previous in PERSONALITY_NAMES and selected in PERSONALITY_NAMES and previous != selected:
            self.personality_changes += 1
            return self.unlock_earned(memory, {"Personality Crisis": self.personality_changes >= 5})
        return []

    def unlock_earned(self, memory, conditions):
        new_achievements = []
        for name, earned in conditions.items():
            if earned and name not in memory.achievements:
                memory.achievements.add(name)
                new_achievements.append(name)
        return new_achievements
