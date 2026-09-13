"""Occasional dialogue surprises; this module never changes player progress."""

import random

# Each entry contains: event name, default message, show a normal answer afterward.
EVENTS = {
    "uncommon": [
        ("hesitation", "The Oracle pauses, listening to something just out of reach...", True),
        ("distracted", "The spirits are distracted. Apparently eternity has a lunch break.", True),
        ("familiar", "That question has a familiar shape. Perhaps I heard it in a dream.", True),
        ("doubt", "I had an answer ready. Now even I wonder whether to trust it.", True),
        ("unclear", "Fate has smudged its handwriting today. Let me try to read it.", True),
        ("curiosity", "You ask interesting questions. Even the silence is paying attention.", True),
    ],
    "rare": [
        ("refusal", "I shall leave that one unanswered. A little mystery suits it.", False),
        ("redirect", "Ask something else. This question has wandered into the wrong prophecy.", False),
        ("conflict", "Certainly yes. Definitely no. Two futures have booked the same appointment.", False),
        ("glimpse", "I peeked behind tomorrow and found a surprise party. Pretend I said nothing.", True),
        ("question", "If tomorrow could ask you one question, what would you hope it asked?", False),
        ("changed_mind", "Yes! Wait, no. I've changed my mind. Please blame the revolving stars.", False),
        ("suspicion", "Curious. Are you testing my wisdom, or am I testing your patience?", True),
    ],
    "extremely_rare": [
        ("echo", "Welcome back from tomorrow. Did you remember to bring the missing minute?", False),
        ("glitch", "[echo misplaced] The answer arrived before the question. Kindly return it.", False),
        ("wrong_oracle", "That question was meant for the Oracle next door. There is no door.", False),
    ],
}

# Selected events have a different voice for every existing personality.
PERSONALITY_MESSAGES = {
    "hesitation": {
        "sage": "Let us be still a moment. The answer has not finished becoming itself.",
        "student": "Hang on. My train of thought just missed its own lecture.",
        "pirate": "Hold fast, matey. The winds be whisperin' two courses at once.",
        "fortune_teller": "The candles hold their breath! Destiny demands a dramatic pause!",
        "wizard": "A moment. Someone has folded the prophecy over the important bit.",
        "alien": "Pausing observation. Your question has made an unusual ripple in local probability.",
        "robot": "Calculating a deliberate pause. Any resemblance to hesitation is statistically false.",
    },
    "refusal": {
        "sage": "This answer is best left sleeping. Let us allow it some peace.",
        "student": "I'm skipping this one. Consider it an elective mystery.",
        "pirate": "Nay, that answer stays in the captain's locked chest today.",
        "fortune_teller": "The curtain shall remain closed! Even destiny deserves a private rehearsal!",
        "wizard": "No prophecy for that one. The scroll and I are on our tea break.",
        "alien": "Translation withheld. The answer appears to be a color humans cannot taste.",
        "robot": "Answer suppressed by my flawless discretion module. This is definitely intentional.",
    },
    "echo": {
        "sage": "You thanked me for this answer tomorrow. I have been wondering why.",
        "student": "Didn't we cover this next Thursday? Great, now time has homework.",
        "pirate": "Ye asked this aboard me ship tomorrow. Funny, I haven't built her yet.",
        "fortune_teller": "We meet again for the first time! The encore has preceded the opening act!",
        "wizard": "You returned my spellbook next winter. Kindly stop bending the calendar.",
        "alien": "I remember your next visit. Humans usually insist on doing those in order.",
        "robot": "Future memory retrieved. Timestamp: yesterday-plus-tomorrow. Perfectly normal operation.",
    },
}


def get_random_event(personality, roll=None):
    """Return None or a message/answer flag/rarity dictionary.

    One roll in [0, 1) selects the tier: 90% normal, 8% uncommon,
    1.8% rare, 0.2% extremely rare. Tests can supply an exact roll.
    """
    if roll is None:
        roll = random.random()
    if not 0 <= roll < 1:
        raise ValueError("Event roll must be at least 0 and less than 1.")
    if roll < 0.90:
        return None
    if roll < 0.98:
        rarity = "uncommon"
    elif roll < 0.998:
        rarity = "rare"
    else:
        rarity = "extremely_rare"

    name, message, show_normal_answer = random.choice(EVENTS[rarity])
    message = PERSONALITY_MESSAGES.get(name, {}).get(personality, message)
    return {"message": message, "show_normal_answer": show_normal_answer, "rarity": rarity}
