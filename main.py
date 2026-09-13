"""Terminal frontend. Run with: python main.py."""

from commands import format_command
from game import OracleGame


def choose_personality():
    personalities = OracleGame.get_personalities()
    choices = {str(number): key for number, key in enumerate(personalities, start=1)}
    while True:
        print("\nChoose a personality:")
        for number, key in choices.items():
            print(f"{number}. {personalities[key]}")
        choice = input("Selection (or quit): ").strip().lower()
        if choice == "quit":
            return None
        if choice in choices:
            return choices[choice]
        print(f"Invalid selection. Please choose a number from 1 to {len(choices)}.")


def announce_achievements(achievements):
    for achievement in achievements:
        try:
            print(f"\n🏆 {achievement} UNLOCKED!")
        except UnicodeEncodeError:
            print(f"\n[Achievement] {achievement} UNLOCKED!")


def display_result(result):
    for line in format_command(result.kind, result.data):
        print(line)
    answer_started = False
    for message in result.messages:
        if message.role == "achievement":
            announce_achievements([message.text])
            continue
        if message.role in {"answer", "event", "awareness", "easter_egg"} and not answer_started:
            print("\nThe Oracle says:")
            answer_started = True
        if message.role in {"topic", "repeat_notice", "safety"}:
            print()
        print(message.text)


def select_from_menu(game):
    selected = choose_personality()
    if selected is None:
        return False
    display_result(game.select_personality(selected))
    return True


def main():
    print("=== THE ORACLE ===")
    try:
        game = OracleGame()
    except (OSError, ValueError) as error:
        print(f"Could not load memory: {error}")
        print("Check memory.json before restarting. Your save has not been changed.")
        return
    print(f"The Oracle remembers {game.memory.questions_asked} previous questions.")
    playing = select_from_menu(game)
    while playing:
        result = game.process_input(input("\nAsk a question (type help for commands, or quit): "))
        display_result(result)
        if result.kind == "quit":
            break
        if result.kind == "select_personality":
            playing = select_from_menu(game)
    print("Farewell, seeker.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nFarewell, seeker.")
