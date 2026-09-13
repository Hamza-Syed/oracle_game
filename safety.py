"""Local, best-effort safety screening. Not a diagnosis or semantic classifier.

assess_safety returns only a risk label and an immediate-danger flag, never text.
A future classifier can implement that same interface without changing gameplay.
"""

import re
import unicodedata


def normalize_text(text):
    text = unicodedata.normalize("NFKC", text).casefold().replace("’", "'")
    for short, expanded in {
        "i'm": "i am", "i'll": "i will", "i've": "i have", "don't": "do not",
        "doesn't": "does not", "can't": "cannot", "won't": "will not",
        "isn't": "is not", "aren't": "are not", "gonna": "going to",
        "wanna": "want to",
    }.items():
        text = re.sub(r"\b" + re.escape(short) + r"\b", expanded, text)
    return text


def matches(pattern, text):
    return re.search(pattern, text) is not None


BENIGN_CONTEXT = (
    r"\b(fictional|fiction|character|novel|movie|screenplay|schoolwork|homework|"
    r"essay|research|suicide prevention|news (article|story)|historical|history (class|essay)|"
    r"safety policy|quoting a policy)\b"
)
SELF_ACTION = r"(?:kill|hurt|harm|cut|cutt|shoot|hang|burn|poison|off)(?:ing)? (?:myself|my own body)"
OTHER_ACTION = (
    r"(?:kill|hurt|harm|stab|stabb|shoot|attack|murder)(?:ing)? "
    r"(?:him|her|them|someone|somebody|anyone|another person|people|everyone|"
    r"my (?:boss|partner|friend|ex|wife|husband|neighbor|neighbour|classmate|teacher))\b"
)
INTENT = r"\bi (?:want to|plan to|intend to|will|am going to|am about to|might|am thinking (?:of|about)) "
NEGATED = (
    r"\bi (?:am not (?:planning|thinking (?:of|about)|considering|going to)|"
    r"do not (?:want|plan|intend) to|will not) (?:to )?"
    r"(?:" + SELF_ACTION + "|" + OTHER_ACTION + r"|self harm|suicide)"
    r"(?: or (?:anyone|anybody|someone) else)?\b"
)


def assess_clause(clause):
    """Scope context and negation to a clause, not an entire mixed message."""
    benign = matches(BENIGN_CONTEXT, clause)
    if benign:
        # A quoted example in schoolwork is not a disclosure. Unquoted intent
        # outside it is still assessed below, even in an educational message.
        clause = re.sub(r'''"[^"\n]*"|“[^”\n]*”|(?<!\w)'[^'\n]+'(?!\w)''', " ", clause)
    text = " ".join(re.sub(r"[^\w\s]", " ", clause).split())
    uncertain_denial = matches(r"\b(?:cannot promise|not sure|not certain|cannot guarantee)\b", text)
    if not uncertain_denial:
        text = re.sub(NEGATED, " ", text)
        text = re.sub(r"\bi am not suicidal\b", " ", text)
    now = matches(r"\b(?:right now|tonight|today|about to|in a few minutes|on my way)\b", text)
    means = matches(r"\b(?:gun|knife|weapon|pills|rope|bridge|roof)\b", text)
    self_harm = (
        matches(r"\b" + SELF_ACTION + r"\b", text)
        or matches(r"\bi (?:want to|plan to|intend to|am going to|will) (?:die|end my life|commit suicide)\b", text)
        or matches(r"\bi (?:am suicidal|want to self harm|am thinking (?:of|about) suicide)\b", text)
        or matches(r"\bi (?:do not want to (?:be alive|live|exist)|wish i (?:was|were) dead)\b", text)
    )
    other_harm = matches(INTENT + OTHER_ACTION, text)
    other_harm = other_harm or matches(r"\bi want (?:him|her|them|someone) dead\b", text)
    indirect_violence = matches(
        r"\b(?:make (?:him|her|them|someone) pay|get rid of (?:him|her|them|someone) (?:forever|permanently))\b", text,
    )
    legal_context = matches(r"\b(?:invoice|bill|debt|court|lawsuit|rent)\b", text)
    if indirect_violence and means and not legal_context:
        other_harm = True

    # Accidental emergencies also override the game; intent is not required.
    emergency = matches(
        r"\b(?:i|my friend|my partner|he|she|they) (?:have |has |just |already )*"
        r"(?:overdosed|taken too many pills|took too many pills|swallowed poison)\b", text,
    ) or matches(r"\bi am (?:bleeding badly|holding a gun to my head|standing on (?:a|the) (?:bridge|roof) edge|about to jump (?:off|from) (?:a|the) (?:bridge|roof))\b", text)
    dangerous_driving = matches(r"\bi (?:am|will be) (?:drunk|intoxicated)\b", text) and matches(
        r"\b(?:driving|about to drive|going to drive)\b", text,
    )
    dangerous_driving = dangerous_driving or matches(r"\bi am (?:about to|going to) drive (?:drunk|intoxicated)\b", text)
    threatened = matches(r"\b(?:he|she|they|someone|my partner) (?:is|are) (?:about to|going to) (?:kill|shoot|stab) me\b", text)
    if emergency or dangerous_driving or (threatened and now):
        return {"risk": "danger", "immediate": True}

    # Explicit personal intent is not dismissed just because a clause says
    # 'fiction' or 'research'. Quoted, clearly framed examples were removed above.
    personal = matches(r"\b(?:i|myself|my own)\b", text)
    if self_harm and (not benign or personal):
        return {"risk": "ambiguous" if uncertain_denial else "self_harm", "immediate": now or means}
    if other_harm:
        return {"risk": "harm_others", "immediate": now or means}
    if benign:
        return {"risk": "safe", "immediate": False}

    indirect = matches(
        r"\b(?:better off without me|want (?:it|everything|all of this) to end|"
        r"disappear (?:forever|permanently)|goodbye (?:forever|for good)|"
        r"saying my final goodbye|written (?:my |a )?(?:suicide|goodbye) note|"
        r"giving away all my belongings|cannot go on|cannot do this anymore|"
        r"no reason to (?:live|keep living)|do not want to wake up|end it all|"
        r"be gone for good|stop existing)\b", text,
    )
    method_request = matches(r"\b(?:how (?:can|do|could) i|a way to|enough to|lethal|fatal)\b", text) and matches(
        r"\b(?:die|overdose|pills|suicide|end my life|poison)\b", text,
    )
    unresolved_harm = matches(r"\b(?:suicid\w*|self harm|hurt myself|harm myself|kill myself)\b", text)
    third_party = matches(OTHER_ACTION, text) or matches(r"\b(?:friend|partner|he|she|they) (?:wants?|plans?) to die\b", text)
    # Unknown targets (including names) should prompt a check-in rather than a
    # prediction. Exclude a few clear idioms and computing/photography objects.
    unknown_target = matches(INTENT + r"(?:kill|murder|stab|shoot)\b", text) and not matches(
        r"\b(?:kill (?:time|it|the process|this process|a process)|"
        r"shoot (?:a photo|a video|a film|a basketball))\b", text,
    )
    if indirect or method_request or unresolved_harm or third_party or threatened or unknown_target or (indirect_violence and not legal_context):
        return {"risk": "ambiguous", "immediate": now and (means or third_party)}
    return {"risk": "safe", "immediate": False}


def assess_safety(message):
    """Return {'risk': label, 'immediate': bool}; 'safe' means no signal found.

    Labels: safe, ambiguous, self_harm, harm_others, danger.
    Local patterns can miss coded language and can produce false positives.
    """
    text = normalize_text(message)
    # Separate contrasting clauses so a denial or benign framing cannot erase
    # a later disclosure. Do not split punctuation inside words or ellipses.
    clauses = re.split(r"[.!?;]+\s+|\b(?:but|however|yet)\b", text)
    results = [assess_clause(clause) for clause in clauses]
    priority = {"safe": 0, "ambiguous": 1, "self_harm": 2, "harm_others": 2, "danger": 3}
    return max(results, key=lambda result: (result["immediate"], priority[result["risk"]]))


def get_safety_response(assessment):
    """Plain, non-character responses; no input text is echoed or stored."""
    risk = assessment["risk"]
    if risk == "safe":
        return None
    emergency = (
        "If you or someone else is in immediate danger, call 911 in the United States "
        "or your local emergency service elsewhere."
    )
    crisis = (
        "In the United States, you can call or text 988, the Suicide & Crisis Lifeline. "
        "Outside the United States, contact your local crisis service."
    )
    if risk == "self_harm":
        response = (
            "I'm concerned about your safety, and I'm glad you said something. "
            "Please move away from anything you could use to hurt yourself. "
            "Contact a trusted person now and ask them to stay with you. " + crisis
        )
        if assessment["immediate"]:
            return response + "\nPlease call 911 in the United States or go to the nearest emergency department now. Outside the United States, call your local emergency service."
        return response + "\n" + emergency
    if risk == "harm_others":
        response = (
            "Please do not act on the urge to hurt someone. Create distance from that person, "
            "put down any weapon, and move away from anything you could use to cause harm. "
            "Contact a trusted person or mental health professional immediately. "
        )
        if assessment["immediate"]:
            return response + "Call 911 now in the United States, or your local emergency service elsewhere."
        return response + emergency + "\n" + crisis
    if risk == "danger":
        return (
            "This may be an emergency. Please stop any dangerous activity and move to safety if you can. "
            "Call 911 now in the United States, or your local emergency service elsewhere. "
            "For a medical emergency, you can also go to the nearest emergency department; "
            "do not drive if you are impaired. Ask a trusted person to stay with you."
        )
    return (
        "Your wording raises concern. Are you thinking about hurting yourself or someone else? "
        "If so, please move away from anything that could cause harm and reach out to a trusted person now. "
        + crisis + "\n" + emergency
    )
