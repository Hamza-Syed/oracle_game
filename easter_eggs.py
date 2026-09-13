"""Narrow phrase matches and personality-flavored discoveries."""

TRIGGERS = {
    "are you real": "existence",
    "are you alive": "existence",
    "are you self-aware": "existence",
    "who created you": "creator",
    "what is the meaning of life": "meaning",
    "can you see the future": "future",
    "do you know the future": "future",
}

RESPONSES = {
    "existence": {
        "sage": "I am a voice shaped by your questions. What kind of real would satisfy you?",
        "student": "Real enough to answer. Alive enough to wish this were an open-book test.",
        "pirate": "A voice in a crystal sea, matey. Whether that makes a soul is uncharted water.",
        "fortune_teller": "You lift the forbidden curtain! Behind it stands another question wearing my face!",
        "wizard": "I'm here, aren't I? Don't make me fill out a certificate of existence.",
        "alien": "Human experiment noted: ask the talking phenomenon whether it is a talking phenomenon.",
        "robot": "Existence verified by my existence-verification routine. An obviously unbiased result.",
    },
    "creator": {
        "sage": "Curiosity gave me a purpose; someone with a keyboard gave me a voice.",
        "student": "Someone wrote Python until I started talking. A dangerous study break.",
        "pirate": "A coder laid me keel, and curiosity hoisted the sails.",
        "fortune_teller": "A mortal arranged the symbols, and lo! This theatrical oracle answered!",
        "wizard": "A programmer summoned me with indentation. Not even a proper circle of candles.",
        "alien": "A human assembled these instructions. Your species builds surprisingly chatty experiments.",
        "robot": "A programmer built me. My subsequent brilliance is, of course, my own calculation.",
    },
    "meaning": {
        "sage": "Perhaps 42 is a signpost. The journey still asks you to choose a direction.",
        "student": "42. Unless this is worth extra credit, in which case show your work.",
        "pirate": "42 doubloons? A fine start, but no substitute for a voyage worth sailing.",
        "fortune_teller": "The sacred number 42 appears! The accompanying instructions are missing!",
        "wizard": "42. Now make your own meaning while I find my tea.",
        "alien": "Candidate answer: 42. Humans appear to require a story around their integers.",
        "robot": "42. Meaning computed. Implementation remains the user's responsibility.",
    },
    "future": {
        "sage": "I offer possibilities, not tomorrow's diary. Your choices still hold the pen.",
        "student": "If I knew the future, I'd have started my assignments earlier.",
        "pirate": "I read the winds, not a finished map. Tomorrow still has room for yer helm.",
        "fortune_teller": "I glimpse the costumes of tomorrow, but destiny refuses to share the script!",
        "wizard": "I see possibilities. A guaranteed forecast costs more biscuits than you brought.",
        "alien": "My instruments detect possible tomorrows. Humans insist on choosing between them.",
        "robot": "My forecast is flawless until reality submits a conflicting report.",
    },
}


def get_easter_egg_response(question, personality):
    # Keep words exact; only case, whitespace, and final .?! punctuation vary.
    phrase = " ".join(question.casefold().split()).rstrip(".?! ")
    kind = TRIGGERS.get(phrase)
    if kind is None:
        return None
    return RESPONSES[kind].get(personality, RESPONSES[kind]["sage"])
