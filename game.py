"""Shared gameplay orchestration, independent of terminal or GUI input/output."""

from dataclasses import dataclass, field

from achievements import AchievementTracker
from commands import get_command_data, get_stats, get_history, get_achievements, COMMAND_HELP
from easter_eggs import get_easter_egg_response
from memories import Memory
from personalities import (
    PERSONALITY_NAMES, get_response, get_topic_reaction, get_conversation_response,
    get_self_evaluation_response, get_preference_response, get_follow_up_category, get_follow_up_response,
    get_vulgar_reaction,
)
from random_events import get_random_event
from self_awareness import get_awareness_message, get_awareness_stage
from safety import assess_safety, get_safety_response


@dataclass
class Message:
    """A displayable message with a role, so interfaces need not parse its text."""
    role: str
    text: str


@dataclass
class GameResult:
    kind: str
    messages: list[Message] = field(default_factory=list)
    new_achievements: list[str] = field(default_factory=list)
    data: dict | list | None = None
    save_error: str | None = None


class OracleGame:
    """One session owns one Memory and one achievement tracker.

    Pass Memory(path) to choose a save location. Construct a new engine with a
    newly loaded Memory for a new session. Startup I/O errors propagate to the UI.
    """

    def __init__(self, memory=None):
        self.memory = memory if memory is not None else Memory()
        self.achievement_tracker = AchievementTracker()
        self.personality = None
        # One last line per personality/stage, only for this running session.
        self.last_awareness_messages = {}
        self.follow_up_personality = None
        self.follow_up_depth = 0

    @staticmethod
    def get_personalities():
        return PERSONALITY_NAMES.copy()

    def get_help(self):
        return COMMAND_HELP.copy()

    def get_stats(self):
        return get_stats(self.memory, self.personality, self.achievement_tracker)

    def get_history(self):
        return get_history(self.memory)

    def get_achievements(self):
        return get_achievements(self.memory, self.achievement_tracker)

    def select_personality(self, personality_id):
        if not isinstance(personality_id, str) or personality_id not in PERSONALITY_NAMES:
            return GameResult("invalid_selection", [Message("notice", "Invalid personality selection.")])
        unlocked = self.achievement_tracker.record_personality_change(
            self.memory, self.personality, personality_id,
        )
        if personality_id != self.personality:
            self._clear_follow_up()
        self.personality = personality_id
        result = GameResult("personality_selected", new_achievements=unlocked)
        if unlocked:
            self._save_progress(result)
            result.messages.extend(Message("achievement", name) for name in unlocked)
        return result

    def _clear_follow_up(self):
        self.follow_up_personality = None
        self.follow_up_depth = 0

    def _record_consultation(self, result):
        # Only final Oracle replies qualify; replacement events alone do not.
        # No answer text or user question is retained as follow-up context.
        if any(message.role in {"answer", "easter_egg"} for message in result.messages):
            self.follow_up_personality = self.personality
            self.follow_up_depth = 0
        return result

    def _respond_to_follow_up(self, category):
        if self.follow_up_personality is None:
            return GameResult("follow_up", [Message("notice", "Ask a new Oracle question first, then we can revisit its reply.")])
        reply = get_follow_up_response(category, self.follow_up_personality)
        self.follow_up_depth += 1
        if self.follow_up_depth >= 2:
            self._clear_follow_up()
        return GameResult("follow_up", [Message("notice", reply)])

    def _save_progress(self, result):
        try:
            self.memory.save_memory()
        except OSError as error:
            result.save_error = str(error)
            result.messages.extend([
                Message("error", f"Could not save memory: {error}"),
                Message("error", "Progress is still in this session; the next question will retry saving."),
            ])

    def process_input(self, user_text):
        question = user_text.strip()
        command = question.lower()
        if command == "quit":
            self._clear_follow_up()
            return GameResult("quit")
        if command == "change":
            return GameResult("select_personality")
        data = get_command_data(command, self.memory, self.personality, self.achievement_tracker)
        if data is not None:
            return GameResult(command, data=data)
        if not question:
            return GameResult("blank", [Message("notice", "Ask a question first, seeker.")])

        assessment = assess_safety(question)
        if assessment["risk"] != "safe":
            self._clear_follow_up()
            return GameResult("safety", [Message("safety", get_safety_response(assessment))])
        vulgar_reaction = get_vulgar_reaction(question, self.personality)
        if vulgar_reaction is not None:
            return GameResult("vulgar_reaction", [Message("notice", vulgar_reaction)])
        follow_up = get_follow_up_category(question)
        if follow_up is not None:
            return self._respond_to_follow_up(follow_up)
        conversation = get_conversation_response(question, self.personality)
        if conversation is not None:
            return GameResult("conversation", [Message("notice", conversation)])
        if self.personality is None:
            return GameResult("select_personality")

        self._clear_follow_up()
        memory = self.memory
        personality = self.personality
        already_asked = memory.has_asked_before(question)
        asked_previous_session = memory.has_asked_in_previous_session(question)
        memory.remember_question(question)
        repeat_number = memory.track_repeat(question)
        memory.used_personalities.add(personality)
        unlocked = self.achievement_tracker.check_achievements(
            memory, repeat_number, asked_previous_session=asked_previous_session,
        )
        result = GameResult("question", new_achievements=unlocked)
        self._save_progress(result)

        easter_egg = get_easter_egg_response(question, personality)
        # Keep discoveries ahead of reflective replies. State was saved once above.
        if easter_egg is None:
            reflective = get_self_evaluation_response(question, personality)
            if reflective is not None:
                result.kind = "self_evaluation"
                result.messages.extend(Message("achievement", name) for name in unlocked)
                result.messages.append(Message("answer", reflective))
                return self._record_consultation(result)
            preference = get_preference_response(question, personality)
            if preference is not None:
                result.kind = "preference"
                result.messages.extend(Message("achievement", name) for name in unlocked)
                result.messages.append(Message("answer", preference))
                return self._record_consultation(result)
        topic = memory.detect_topic(question)
        reaction = get_topic_reaction(personality, topic)
        event = None
        awareness = None
        if easter_egg is None:
            event = get_random_event(personality)
            if event is None or event["rarity"] != "extremely_rare":
                key = (personality, get_awareness_stage(memory.questions_asked))
                previous = self.last_awareness_messages.get(key)
                options = {} if previous is None else {"previous_message": previous}
                awareness = get_awareness_message(personality, memory.questions_asked, **options)
                if awareness is not None:
                    self.last_awareness_messages[key] = awareness

        if reaction:
            result.messages.append(Message("topic", reaction))
        if already_asked:
            result.messages.append(Message("repeat_notice", "The Oracle narrows its eyes. You have asked this before..."))
        if repeat_number == 2:
            result.messages.append(Message("repeat", "You seem concerned about this."))
        elif repeat_number == 3:
            result.messages.append(Message("repeat", "The answer may not change simply because you ask again."))
        elif repeat_number >= 5:
            result.messages.append(Message("repeat", "You seek certainty where none exists."))
        result.messages.extend(Message("achievement", name) for name in unlocked)

        if easter_egg is not None:
            result.kind = "easter_egg"
            result.messages.append(Message("easter_egg", easter_egg))
            return self._record_consultation(result)
        if event:
            result.kind = "event"
            result.data = event.copy()
            result.messages.append(Message("event", event["message"]))
        if awareness:
            result.messages.append(Message("awareness", awareness))
        if event is None or event["show_normal_answer"]:
            result.messages.append(Message("answer", get_response(personality)))
        return self._record_consultation(result)
