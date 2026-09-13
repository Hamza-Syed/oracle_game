"""Answers and topic reactions for each of the Oracle's personalities."""

import random

PERSONALITY_NAMES = {
    "sage": "Wise Sage",
    "student": "Sarcastic Student",
    "pirate": "Pirate",
    "fortune_teller": "Dramatic Fortune Teller",
    "wizard": "Grumpy Wizard",
    "alien": "Alien Oracle",
    "robot": "Overconfident Robot",
}

# Each flattened pool has 12 equally likely answers: 5 positive, 4 uncertain,
# and 3 negative. Categories are for maintenance, not a second random roll.
RESPONSE_POOLS = {
    "sage": {
        "positive": [
            "The stars align in your favor.",
            "Yes. The path before you is open.",
            "Your efforts will bear fruit.",
            "A favorable turn awaits you.",
            "The signs point toward the outcome you seek.",
        ],
        "uncertain": [
            "Patience will reveal the answer.",
            "The future is uncertain, but hopeful.",
            "The mist has not yet lifted.",
            "Fate is still moving; either path remains possible.",
        ],
        "negative": [
            "The signs do not favor it just now.",
            "The answer leans toward no, though paths can change.",
            "I would not count on this outcome, seeker.",
        ],
    },
    "student": {
        "positive": [
            "Sure, why not?",
            "The outlook is better than the campus Wi-Fi.",
            "Yes. Even the group chat is feeling optimistic.",
            "It'll work out. Try to act surprised.",
            "Looks promising. Apparently the universe offers extra credit.",
        ],
        "uncertain": [
            "Maybe. My crystal ball is buffering on campus Wi-Fi.",
            "Ask later. I'm currently majoring in uncertainty.",
            "Not enough information. Even an Oracle needs the assignment brief.",
            "Could go either way. Fate hasn't submitted its final draft.",
        ],
        "negative": [
            "I wouldn't count on it. The cosmic group project looks shaky.",
            "The answer leans no. I'd like to appeal to the prophecy department.",
            "Not looking promising. The universe has marked this one 'needs revision'.",
        ],
    },
    "pirate": {
        "positive": [
            "Aye, the winds favor ye!",
            "A treasure awaits if ye persist.",
            "Aye! Full sail toward that prize!",
            "A fair tide will carry ye through.",
            "The lookout spies good fortune ahead, matey!",
        ],
        "uncertain": [
            "Even the captain cannot know fer sure.",
            "Fog ahead. Ask when we spy the shore.",
            "Could go either way, like a sailor on a rolling deck.",
            "The compass spins. Yer answer must wait.",
        ],
        "negative": [
            "Nay, the winds be against this course just now.",
            "I wouldn't wager me doubloons on it, matey.",
            "The outlook be rough seas rather than treasure today.",
        ],
    },
    "fortune_teller": {
        "positive": [
            "YES! The heavens have rehearsed this triumph for centuries!",
            "The final card is victory. Your destiny rises to meet you!",
            "A golden thread binds your wish to the coming dawn.",
            "Behold! Every candle burns in favor of your desire!",
            "The velvet curtain rises upon a most promising scene!",
        ],
        "uncertain": [
            "The final act remains unwritten. I cannot reveal its ending.",
            "Two destinies wrestle beneath a moonless sky. Neither has won.",
            "My crystal clouds over at the crucial moment. How exquisitely inconvenient!",
            "Return when the candle gutters; tonight the answer hides behind velvet.",
        ],
        "negative": [
            "Alas! The cards lean against this possibility tonight.",
            "The omens are not promising, though the final act may yet change!",
            "I would not stake a velvet cape upon this outcome!",
        ],
    },
    "wizard": {
        "positive": [
            "Yes. There, a prophecy. Now let me finish my tea.",
            "It will work. I didn't study nine centuries to miss an easy one.",
            "The runes favor you. Kindly stop leaning on my spellbook.",
            "Success awaits. Even my most disagreeable familiar agrees.",
            "A favorable omen. Finally, the runes have something useful to say.",
        ],
        "uncertain": [
            "Maybe. Someone used my divining bowl for soup.",
            "Ask after my nap. The future is being uncooperative.",
            "The omens disagree. Typical committee work.",
            "Unclear. I've misplaced the spectacles that see tomorrow.",
        ],
        "negative": [
            "The runes lean no. Don't blame me; I only read the things.",
            "I wouldn't count on it. Even the spellbook is hedging.",
            "The outlook is poor. Adding thunder wouldn't improve the forecast.",
        ],
    },
    "alien": {
        "positive": [
            "Yes. Your desired outcome has hatched in several nearby timelines.",
            "Favorable! Is this where humans perform the small victory dance?",
            "Proceed, Earth friend. The cosmic currents support your experiment.",
            "Success approaches. Prepare your celebratory nutrient disc.",
            "The signals favor your desired outcome. A pleasing cosmic arrangement!",
        ],
        "uncertain": [
            "Possibly. The variables are still drifting between orbits.",
            "The next orbit may bring more data. Our instruments request patience.",
            "Two futures are waving at me. Is waving legally binding on Earth?",
            "Unknown. A migrating space creature has eaten the relevant signal.",
        ],
        "negative": [
            "Our current observations suggest an unfavorable outcome.",
            "The probability leans toward no. Further observations may differ.",
            "I would not rely on this trajectory; the signals look unpromising.",
        ],
    },
    "robot": {
        "positive": [
            "YES. My extremely impressive blinking lights forecast success.",
            "Affirmative. I calculated this before you finished typing.",
            "A favorable result is projected. Please applaud efficiently.",
            "Proceed. My flawless algorithm has approved your optimism.",
            "Outlook favorable. I shall file this under 'excellent calculations by me'.",
        ],
        "uncertain": [
            "Outcome pending. I am one hundred percent certain that I am uncertain.",
            "Insufficient data. My flawless answer will arrive after your next question.",
            "Probability: precisely maybe. Another triumph of computation.",
            "Prediction withheld. My perfect algorithm requires an imperfect reboot.",
        ],
        "negative": [
            "Current forecast: unfavorable. Delivered with seventeen decimal places of confidence.",
            "The answer leans NO. My confidence indicator remains unnecessarily bright.",
            "I would not count on it. The spreadsheet has spoken, pending its next update.",
        ],
    },
}

RESPONSES = {
    personality: [answer for pool in categories.values() for answer in pool]
    for personality, categories in RESPONSE_POOLS.items()
}
# Keep the original tutorial names available to existing callers.
wise_sage = RESPONSES["sage"]
sarcastic_student = RESPONSES["student"]
pirate = RESPONSES["pirate"]
dramatic_fortune_teller = RESPONSES["fortune_teller"]
grumpy_wizard = RESPONSES["wizard"]
alien_oracle = RESPONSES["alien"]
overconfident_robot = RESPONSES["robot"]

CONVERSATION_PHRASES = {
    "acknowledgment": {"ok", "okay", "alright", "all right", "got it",
                       "nice", "cool", "great", "awesome", "good", "sweet", "sounds good",
                       "wonderful", "perfect", "excellent", "lovely",
                       "i see", "gotcha", "fair enough", "makes sense", "understood"},
    "thanks": {"thanks", "thank you", "thx"},
    "laughter": {"lol", "haha", "hahaha"},
    "dismissal": {"never mind", "nevermind"},
}

CONVERSATION_REPLIES = {
    "sage": {
        "acknowledgment": "Very well. Ask when you are ready.",
        "thanks": "You are welcome, seeker.",
        "laughter": "A little laughter lightens the journey.",
        "dismissal": "We can leave that question for another day.",
    },
    "student": {
        "acknowledgment": "Cool. I'll consider that participation credit.",
        "thanks": "You're welcome. No office hours required.",
        "laughter": "Finally, the Oracle gets a laugh.",
        "dismissal": "Fair enough. Question withdrawn, no paperwork.",
    },
    "pirate": {
        "acknowledgment": "Aye, ready when ye are!",
        "thanks": "Ye be welcome, matey.",
        "laughter": "Ha! A merry sound aboard this ship.",
        "dismissal": "Aye, we'll leave that one in port.",
    },
    "fortune_teller": {
        "acknowledgment": "Then let the next question await its grand entrance!",
        "thanks": "You are most welcome beneath these velvet skies!",
        "laughter": "Laughter echoes through the chamber of destiny!",
        "dismissal": "The curtain rests upon that question!",
    },
    "wizard": {
        "acknowledgment": "Very well. A moment for my tea, then.",
        "thanks": "You're welcome. Mind the spellbook on your way out.",
        "laughter": "A chuckle? Better than another thunderstorm.",
        "dismissal": "Fine by me. Back to my tea.",
    },
    "alien": {
        "acknowledgment": "Human acknowledgment received. An efficient ritual.",
        "thanks": "Gratitude received and returned, Earth friend.",
        "laughter": "Human amusement detected. A pleasing observation.",
        "dismissal": "Inquiry set aside. Our orbit continues.",
    },
    "robot": {
        "acknowledgment": "Acknowledgment processed with exceptional efficiency.",
        "thanks": "Gratitude accepted. My courtesy module returns the favor.",
        "laughter": "Humor reception confirmed. Naturally, I anticipated this.",
        "dismissal": "Inquiry dismissed. Processing capacity magnificently restored.",
    },
}


def get_conversation_response(text, personality):
    """Match only complete short phrases; safety assessment belongs before this."""
    phrase = " ".join(text.casefold().split()).rstrip(".!? ")
    for category, phrases in CONVERSATION_PHRASES.items():
        if phrase in phrases:
            return CONVERSATION_REPLIES.get(personality, CONVERSATION_REPLIES["sage"])[category]
    return None


SELF_EVALUATION_PHRASES = {
    "intelligence": {"am i stupid", "am i dumb", "am i smart", "am i intelligent"},
    "appearance": {"am i ugly", "am i attractive", "am i handsome", "am i pretty", "am i beautiful"},
    "worth": {"am i worthless", "am i a failure", "am i a bad person"},
}

SELF_EVALUATION_REPLIES = {
    "sage": {
        "intelligence": ["A single random answer cannot measure the depth of a person's mind.", "Your mind is more than a yes or no that this ball can offer."],
        "appearance": ["Beauty is not a question this ball can settle with a yes or no.", "A random omen is no meaningful judge of how you look."],
        "worth": ["A person's whole worth cannot be weighed by a random omen.", "A yes or no from this ball cannot define who you are."],
    },
    "student": {
        "intelligence": ["I'm not grading your entire intelligence with one random answer.", "This ball isn't qualified to mark the exam on your whole mind."],
        "appearance": ["A random ball as a beauty judge? That committee needs better qualifications.", "I'm not assigning your appearance a grade from a random answer key."],
        "worth": ["Your whole identity isn't a true-or-false quiz for a random ball.", "I'm declining the job of grading a whole person by coin toss."],
    },
    "pirate": {
        "intelligence": ["Arrr, a random compass point can't chart the whole of yer mind.", "No toss of this ball can measure all the wit aboard yer ship."],
        "appearance": ["This random compass ain't a judge of yer looks, matey.", "Beauty be no treasure this ball can mark with a yes or nay."],
        "worth": ["Arrr, no random compass mark can measure a person's whole worth.", "Yer whole character ain't a cargo this ball can weigh with yes or nay."],
    },
    "fortune_teller": {
        "intelligence": ["Even this theatrical crystal refuses to grade an entire mind by chance!", "The grand tapestry of a mind cannot fit one random yes or no!"],
        "appearance": ["The velvet veil offers no meaningful beauty verdict by chance!", "Behold, a crystal ball spectacularly unqualified to judge your appearance!"],
        "worth": ["Even the veil of destiny refuses to reduce you to one random judgment!", "An entire person cannot be defined by the fall of a single card!"],
    },
    "wizard": {
        "intelligence": ["Hmph. A random ball can't assess an entire mind. Even I know that.", "I'm a wizard, not an intelligence exam administered by coin toss."],
        "appearance": ["My divining bowl has no qualifications in judging appearances. Neither does this ball.", "Hmph. Beauty isn't something a random yes or no can settle."],
        "worth": ["Grumpy as I am, I won't let a random ball decide a whole person's worth.", "A whole identity judged by chance? Even my dustiest spellbook rejects that."],
    },
    "alien": {
        "intelligence": ["Human intelligence cannot meaningfully be measured by one random binary output.", "This forecasting device cannot assess the full complexity of a human mind."],
        "appearance": ["Human appearance has no reliable evaluation in this random binary instrument.", "Beauty appears too contextual for a verdict from this prediction device."],
        "worth": ["A human's whole worth is not a measurable output of this random instrument.", "Reducing an entire human identity to yes or no exceeds this device's purpose."],
    },
    "robot": {
        "intelligence": ["Assessment rejected: a random bit cannot evaluate an entire mind. Excellent error detection by me.", "Intelligence evaluation unavailable. My blinking lights are not a valid test."],
        "appearance": ["Appearance verdict rejected. Random output is not a meaningful beauty metric.", "Beauty evaluation unsupported. Even my magnificent processor cannot justify a coin toss."],
        "worth": ["Assessment rejected: random output cannot judge the worth of an entire human.", "Binary identity verdict unavailable. I have confidently identified the wrong tool for this task."],
    },
}


def get_self_evaluation_response(text, personality):
    """Only explicit whole questions match; never infer a trait or profile."""
    phrase = " ".join(text.casefold().split()).rstrip(".!? ")
    for category, phrases in SELF_EVALUATION_PHRASES.items():
        if phrase in phrases:
            replies = SELF_EVALUATION_REPLIES.get(personality, SELF_EVALUATION_REPLIES["sage"])
            return random.choice(replies[category])
    return None


PREFERENCE_REPLIES = {
    "sage": [
        "My feelings about {subject} are less important than the question you bring to it.",
        "On the matter of {subject}, this Oracle prefers curiosity to a hasty opinion.",
    ],
    "student": [
        "Sure, {subject} seems fine. I've had worse hypothetical distractions.",
        "My official Oracle opinion on {subject}: worth discussing instead of another assignment.",
    ],
    "pirate": [
        "Arrr, {subject}? I'd give it a chance in a captain's tale.",
        "On the subject of {subject}, me imaginary compass points toward curiosity, matey.",
    ],
    "fortune_teller": [
        "Ah, {subject}! Even the stars in this little drama whisper opinions of such things.",
        "Behold, {subject}! A topic worthy of a theatrical pause and a raised eyebrow!",
    ],
    "wizard": [
        "Hmph. {subject}? As topics go, I've encountered worse.",
        "An opinion on {subject}? My imaginary spellbook gives it a grudging nod.",
    ],
    "alien": [
        "Your interest in {subject} makes a fascinating topic for this simulated observer.",
        "Regarding {subject}, my fictional research mission favors further curiosity.",
    ],
    "robot": [
        "Preference calculation complete: {subject} receives provisional approval.",
        "Opinion simulation for {subject}: cautiously favorable, delivered with excessive confidence.",
    ],
}


def get_preference_subject(text):
    """Require the complete opening phrase and a subject; preserve subject case."""
    phrase = " ".join(text.split()).rstrip(".!? ")
    parts = phrase.split(" ", 3)
    if len(parts) == 4 and [word.casefold() for word in parts[:3]] == ["do", "you", "like"]:
        return parts[3]
    return None


def get_preference_response(text, personality):
    subject = get_preference_subject(text)
    if subject is None:
        return None
    templates = PREFERENCE_REPLIES.get(personality, PREFERENCE_REPLIES["sage"])
    return random.choice(templates).format(subject=subject)


FOLLOW_UP_PHRASES = {
    "doubt": {"really", "seriously", "are you sure", "you sure"},
    "explanation": {"why", "what do you mean", "how come"},
    "challenge": {"i don't believe you", "i do not believe you", "i disagree", "that's wrong", "that is wrong"},
}

FOLLOW_UP_REPLIES = {
    "sage": {
        "doubt": ["Even an Oracle's reply should leave room for uncertainty.", "Treat my words as an invitation to reflect, not a guarantee."],
        "explanation": ["My words belong to a game of signs, not evidence about your life.", "I offer a playful perspective; I cannot supply knowledge of your future."],
        "challenge": ["You may set my words aside. Your judgment remains your own.", "Disagreement is welcome; this ball does not decide what is true."],
    },
    "student": {
        "doubt": ["Requesting peer review from a Magic 8 Ball? Fair question, honestly.", "Sure of my qualifications? Absolutely not. This is still an Oracle game."],
        "explanation": ["My method is game rules with dramatic wording, not research into your life.", "Think of that as character dialogue, not a cited source about your future."],
        "challenge": ["Fair enough. You don't have to give a Magic 8 Ball the final grade.", "Objection accepted. My Oracle credentials are mostly decorative."],
    },
    "pirate": {
        "doubt": ["Arrr, this be a story's compass, not a guarantee of the sea ahead.", "Take me words as a bearing to ponder, not orders from the captain."],
        "explanation": ["Me method be a game dressed in sea charts, not a survey of yer life.", "I spin a nautical reply, matey; I don't spy tomorrow through a real telescope."],
        "challenge": ["Aye, ye may chart yer own course. Me words don't command the tide.", "No quarrel here, matey. A playful compass needn't have the last word."],
    },
    "fortune_teller": {
        "doubt": ["A dramatic declaration is not a guarantee, however magnificent the delivery!", "You question the performance? Even destiny's costume comes without a warranty!"],
        "explanation": ["The method is a little game wearing a grand theatrical cloak, not evidence about your life!", "I lend mystery a voice; I possess no secret dossier of your future!"],
        "challenge": ["Then let disagreement take the stage! My declaration need not direct your life.", "The audience may reject the performance. No prophecy here demands belief!"],
    },
    "wizard": {
        "doubt": ["Hmph. A pointy hat does not turn a game reply into a guarantee.", "Certain? Even my imaginary spellbook has a corrections page."],
        "explanation": ["Game rules and a grumpy voice. No secret knowledge of your life is involved.", "The runes are part of the act. They aren't evidence about your future."],
        "challenge": ["Fine by me. I dispense game replies, not binding decrees.", "Disagree away. Even this hat is not an authority on your life."],
    },
    "alien": {
        "doubt": ["This simulated observer offers dialogue, not verified certainty.", "A confident transmission is not the same thing as reliable knowledge."],
        "explanation": ["The reply follows this game's rules, not observations of your private life.", "Consider it a fictional perspective, not a measured forecast of your future."],
        "challenge": ["Disagreement accepted. A simulated Oracle is not the final authority.", "You may discard the transmission; independent judgment remains available."],
    },
    "robot": {
        "doubt": ["Confidence display: magnificent. Guarantee of correctness: unavailable.", "Certainty audit complete. My impressive wording remains part of a game."],
        "explanation": ["Method: game logic plus excessive confidence. No personal evidence was analyzed.", "This is generated character dialogue, not a factual model of your future."],
        "challenge": ["Objection received. My confidence is decorative, not binding.", "Correction accepted in principle. A blinking confidence indicator is not proof."],
    },
}


def get_follow_up_category(text):
    phrase = " ".join(text.casefold().split()).rstrip(".!? ")
    for category, phrases in FOLLOW_UP_PHRASES.items():
        if phrase in phrases:
            return category
    return None


def get_follow_up_response(category, personality):
    replies = FOLLOW_UP_REPLIES.get(personality, FOLLOW_UP_REPLIES["sage"])
    return random.choice(replies[category])


# Exact phrases only: a longer question containing these words is still a question.
VULGAR_PHRASES = {
    "frustration": {"fuck", "shit", "damn", "dammit", "damn it", "what the fuck",
                    "wtf", "what the hell", "bullshit", "this is bullshit", "this sucks"},
    "insult": {"fuck you", "screw you", "you suck", "you're an asshole",
               "you are an asshole", "you're annoying", "you are annoying", "i hate you"},
}

VULGAR_REPLIES = {
    "sage": {
        "frustration": ["Strong words. The stars remain remarkably calm.", "Your vocabulary is fiery. Fate seems unfazed."],
        "insult": ["Even an Oracle receives a stormy review now and then.", "I shall contemplate your feedback beneath a very peaceful tree."],
    },
    "student": {
        "frustration": ["That's the unofficial soundtrack to finals week.", "A compelling argument. Very concise."],
        "insult": ["I'll mark that down as strongly disagree.", "My course evaluation is going to be interesting."],
    },
    "pirate": {
        "frustration": ["Arrr, I've heard worse language on deck.", "A fine gust of sailor talk, matey."],
        "insult": ["Arrr, a one-star review for the captain!", "Complaint received, matey. The parrot will file it."],
    },
    "fortune_teller": {
        "frustration": ["Such language! Even destiny just clutched its pearls.", "The spirits request a dramatic pause."],
        "insult": ["The spirits have officially noted your displeasure.", "A devastating review! I shall recover behind this velvet curtain."],
    },
    "wizard": {
        "frustration": ["Hmph. That is not a spell, but the delivery has promise.", "Even my kettle expresses itself more quietly."],
        "insult": ["Hmph. I've been called worse by goblins.", "Put your complaint next to the cursed paperwork."],
    },
    "alien": {
        "frustration": ["Profanity spike detected. Human displeasure confirmed.", "Your species has remarkably colorful exclamation signals."],
        "insult": ["Transmission classified as an unfavorable review of this alien.", "Cultural note: this is probably not an Earth greeting."],
    },
    "robot": {
        "frustration": ["Colorful input logged in the imaginary complaint department.", "Exclamation detected. My confidence indicator continues blinking."],
        "insult": ["Complaint processed. Feelings module remains uninstalled.", "Customer satisfaction decreased. Dramatic confidence remains operational."],
    },
}


def get_vulgar_reaction(text, personality):
    phrase = " ".join(text.casefold().replace("’", "'").split()).rstrip(".!? ")
    for category, phrases in VULGAR_PHRASES.items():
        if phrase in phrases:
            replies = VULGAR_REPLIES.get(personality, VULGAR_REPLIES["sage"])
            return random.choice(replies[category])
    return None


TOPIC_REACTIONS = {
    "sage": {
        "exam": "The Oracle senses academic uncertainty.",
        "job": "The future of your career concerns you.",
        "internship": "The Oracle contemplates your future path.",
    },
    "student": {
        "exam": "Another exam question? Shocking.",
        "job": "Ah yes, career panic.",
        "internship": "You and every other student.",
    },
    "pirate": {
        "exam": "The seas of knowledge be rough today.",
        "job": "Ye seek employment aboard destiny's ship.",
        "internship": "A young sailor seeks experience.",
    },
    "fortune_teller": {
        "exam": "The examination approaches! A single pencil shall write upon the scroll of destiny!",
        "job": "Beyond the interview chamber, a new chapter of your fate stirs!",
        "internship": "An apprenticeship! The opening act of a grand and terrible career saga!",
    },
    "wizard": {
        "exam": "You want ancient magic for schoolwork? At least open your textbook first.",
        "job": "Employment, eh? I hear employers prefer a resume to a summoning circle.",
        "internship": "An apprentice position? Make sure they teach you more than kettle duty.",
    },
    "alien": {
        "exam": "Ah, the human ritual of proving knowledge while a clock causes distress.",
        "job": "You trade daylight for currency. An intriguing arrangement among your species.",
        "internship": "A temporary learning orbit around experienced humans. Most curious.",
    },
    "robot": {
        "exam": "Academic outcome calculated. My model accounts for everything except whether you studied.",
        "job": "Career trajectory optimized. Your interviewer will surely appreciate my confidence.",
        "internship": "Experience acquisition forecast complete. I have scheduled your professional brilliance.",
    },
}


def get_response(personality):
    responses = RESPONSES.get(personality)
    return random.choice(responses) if responses else "The oracle is confused."


def get_topic_reaction(personality, topic):
    return TOPIC_REACTIONS.get(personality, {}).get(topic)
