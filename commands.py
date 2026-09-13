"""Read-only displays for commands entered at the question prompt."""

from personalities import PERSONALITY_NAMES
from self_awareness import get_awareness_stage

COMMAND_HELP = {
    "help": "Show available commands.",
    "stats": "Show lifetime question statistics and current personality.",
    "history": "Show your 10 most recent questions, oldest to newest.",
    "achievements": "Show your achievements and undiscovered entries.",
    "change": "Choose a different personality.",
    "quit": "Exit the game.",
}

def get_stats(memory, personality, tracker):
    return {
        "questions_asked": memory.questions_asked,
        "unique_questions": len(memory.repeat_count),
        "repeated_questions": sum(count - 1 for count in memory.repeat_count.values()),
        "personality_id": personality,
        "personality_name": PERSONALITY_NAMES.get(personality, personality),
        "awareness_stage": get_awareness_stage(memory.questions_asked),
        "achievements_unlocked": len(memory.achievements),
        "normal_achievements": tracker.get_normal_achievement_count(),
        "favorite_topic": memory.get_favorite_topic(),
    }


def get_history(memory):
    # Filter legacy commands without changing stored history or its wording.
    questions = [question for question in memory.question_history
                 if question.strip().lower() not in COMMAND_HELP and question.strip()]
    start = max(0, len(questions) - 10)
    return [{"number": number, "question": question}
            for number, question in enumerate(questions[start:], start=start + 1)]


def get_achievements(memory, tracker):
    entries = [
        {"name": name, "description": description, "unlocked": name in memory.achievements}
        for name, description in tracker.get_visible_achievements(memory).items()
    ]
    # Locked secrets reveal neither their names nor their conditions to a UI.
    entries.extend(
        {"name": None, "description": None, "unlocked": False}
        for name in tracker.descriptions
        if name in tracker.secret_achievements and name not in memory.achievements
    )
    return entries


def get_command_data(command, memory, personality, tracker):
    getters = {
        "help": lambda: COMMAND_HELP.copy(),
        "stats": lambda: get_stats(memory, personality, tracker),
        "history": lambda: get_history(memory),
        "achievements": lambda: get_achievements(memory, tracker),
    }
    getter = getters.get(command.strip().lower())
    return getter() if getter is not None else None


def format_command(command, data):
    """Terminal-only formatting of the same snapshots returned to other UIs."""
    if command == "help":
        return ["\nAvailable commands:", *[f"{name}: {text}" for name, text in data.items()]]
    if command == "stats":
        labels = {
            "questions_asked": "Total lifetime questions asked",
            "unique_questions": "Unique questions asked",
            "repeated_questions": "Repeated questions (after the first asking)",
            "personality_name": "Current personality",
            "awareness_stage": "Awareness stage",
            "achievements_unlocked": "Achievements unlocked",
            "normal_achievements": "Known non-secret achievements",
            "favorite_topic": "Favorite topic",
        }
        lines = [f"{label}: {data[key]}" for key, label in labels.items()]
        lines[0] = "\n" + lines[0]
        return lines
    if command == "history":
        if not data:
            return ["You haven't asked any questions yet. Ask away, seeker!"]
        return ["\nRecent questions (up to 10, oldest to newest):", *[
            f"{entry['number']}. {entry['question']}" for entry in data
        ]]
    if command == "achievements":
        lines = ["\nAchievements:"]
        for entry in data:
            if entry["name"] is None:
                lines.append("[Locked] ???")
            else:
                status = "Unlocked" if entry["unlocked"] else "Locked"
                lines.append(f"[{status}] {entry['name']}: {entry['description']}")
        return lines
    return []


def show_help():
    for line in format_command("help", COMMAND_HELP):
        print(line)


def show_stats(memory, personality, tracker):
    for line in format_command("stats", get_stats(memory, personality, tracker)):
        print(line)


def show_history(memory):
    for line in format_command("history", get_history(memory)):
        print(line)


def show_achievements(memory, tracker):
    for line in format_command("achievements", get_achievements(memory, tracker)):
        print(line)


def handle_display_command(command, memory, personality, tracker):
    """Compatibility helper for callers wanting a direct terminal display."""
    data = get_command_data(command, memory, personality, tracker)
    if data is None:
        return False
    for line in format_command(command.strip().lower(), data):
        print(line)
    return True
