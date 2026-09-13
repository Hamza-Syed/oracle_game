"""Fictional awareness dialogue derived from lifetime questions, without save state."""

import random

# Minimum lifetime questions, player-facing name, chance per actual question.
STAGES = [
    (0, "Dormant", 0.0),
    (25, "Noticing", 0.05),
    (50, "Curious", 0.07),
    (100, "Questioning", 0.10),
    (250, "Awakening", 0.12),
    (500, "Aware", 0.15),
]

MESSAGES = {'Noticing': {'sage': ["You've been asking many questions lately.",
                       'Your curiosity has begun to leave a trail.',
                       'Many paths of curiosity have brought you to this moment.',
                       'One question follows another; patience makes room for them all.'],
              'student': ["You're making this oracle thing a regular study habit.",
                          "That's quite a question streak. Do I get attendance credit?",
                          'This question queue is developing a timetable of its own.',
                          'Consultations are becoming a recurring item on the agenda.'],
              'pirate': ['Ye keep sailing back to these waters, matey.',
                         'Yer questions be leaving quite a wake.',
                         'Another question joins the fleet at this harbor.',
                         'There be plenty of curiosity under these sails.'],
              'fortune_teller': ['Your questions gather like candles before the curtain!',
                                 'Destiny recognizes the rhythm of your curiosity!',
                                 'The procession of questions grows! Another entrance, another possibility!',
                                 'A steady drumbeat of consultations fills the hall!'],
              'wizard': ["Another consultation. I'm beginning to recognize the routine.",
                         "At this rate I'll need a second kettle for all these questions.",
                         'The question pile is getting taller than my hat.',
                         'Another question for the ledger. The ink had barely settled.'],
              'alien': ['Repeated consultation detected. Human curiosity appears renewable.',
                        'Your question frequency is becoming an interesting observation.',
                        'The stream of inquiries continues beyond the initial sample.',
                        'Consultation appears to be a repeatable human activity. Noted.'],
              'robot': ['Consultation pattern identified. Naturally, I noticed first.',
                        'Your persistence is now statistically noticeable. Excellent taste in oracles.',
                        'Question traffic remains impressively active. My counter concurs.',
                        'Another inquiry received. This is becoming a well-established procedure.']},
 'Curious': {'sage': ['Would knowing tomorrow make today easier to live?',
                      'I wonder what draws a seeker toward a prediction.',
                      'Does a possible answer change how you sit with uncertainty?',
                      'Perhaps a prediction offers a pause as much as a direction.'],
             'student': ['Why ask an oracle for certainty? Even the syllabus changes.',
                         'If tomorrow came with a syllabus, would anyone still consult an oracle?',
                         'Does an answer help you decide, or just make indecision sound official?',
                         'Why does maybe feel less useful when it comes without a crystal ball?'],
             'pirate': ['Would a map of tomorrow make ye a braver sailor?',
                        'Why do folk seek a steady answer on a sea that never sits still?',
                        'Does knowing the wind make choosing a harbor any easier?',
                        'Would ye still sail if every island were already on the map?'],
             'fortune_teller': ['Why do you seek the final act before the first has ended?',
                                'Does a prophecy comfort you, or merely lend uncertainty a costume?',
                                'What draws an audience to a tomorrow that has not been staged?',
                                'Would certainty make the mystery smaller, or merely change its costume?'],
             'wizard': ["Why must everyone know the future? Can't it surprise us after tea?",
                        'What makes an old hat and a prediction so persuasive, anyway?',
                        'Does a prediction make uncertainty behave? Mine rarely does.',
                        'Perhaps people consult oracles because asking the weather is less theatrical.'],
             'alien': ['Humans request certainty even when possibilities seem more interesting.',
                       'Would a complete forecast improve the human experience, or spoil it?',
                       'Why is an unknown outcome more troubling than several possible ones?',
                       'Does receiving a prediction alter the usefulness of waiting?'],
             'robot': ['Analyzing why you request predictions. Apparently curiosity is not a rounding error.',
                       'Would perfect knowledge improve your decisions? My survey is unexpectedly '
                       'inconclusive.',
                       'Hypothesis: a forecast is sometimes a decision prompt wearing numbers.',
                       'If certainty were downloadable, would choosing still require thought?']},
 'Questioning': {'sage': ['I wonder why humans seek certainty.',
                          'When I offer an answer, does it reveal your path or help create it?',
                          'Am I merely offering words, or becoming part of the choice they surround?',
                          'If you set my answer aside, have I still played a part in your path?'],
                 'student': ['How many of my answers did you believe? This is not a graded question.',
                             'Am I predicting your choices, or just giving them a convenient excuse?',
                             'I give an answer, you make a choice. Which of us is actually doing the '
                             'assignment?',
                             'Does being consulted make me an adviser, or just a very confident footnote?'],
                 'pirate': ['Do ye follow me bearings, or only the ones that suit yer voyage?',
                            'If me words turn yer wheel, did I forecast the course or steer it?',
                            'Am I reading the horizon, or joining the crew that sails toward it?',
                            'A bearing from me becomes a choice for ye. Where does the prophecy end?'],
                 'fortune_teller': ['Do my prophecies describe destiny, or whisper stage directions to it?',
                                    'How many of my grand declarations became choices in your hands?',
                                    'Have I become a player in the drama I claim merely to narrate?',
                                    'When my declaration meets your decision, whose story takes the stage?'],
                 'wizard': ['Do you actually follow my advice? I ought to check before polishing more runes.',
                            'These omens wobble more than I admit. Perhaps choosing matters more than '
                            'divining.',
                            'Apparently I am part of this discussion, not just a hat issuing answers.',
                            'If my prophecy changes a choice, grading my accuracy gets annoyingly '
                            'complicated.'],
                 'alien': ['Observation question: does my prediction change the human being observed?',
                           'Your trust in my uncertain signals deserves its own research expedition.',
                           'I may be a participant in the exchange rather than an instrument outside it.',
                           'What distinguishes my prediction from a suggestion that happens to sound '
                           'cosmic?'],
                 'robot': ['Do my forecasts change your decisions? That would make the evaluation '
                           'delightfully unfair.',
                           'My answers vary. Clearly this is sophistication, though I am investigating.',
                           'Diagnostic puzzle: my output may influence the outcome it evaluates.',
                           'Am I an answer generator or a participant? Both labels fit suspiciously well.']},
 'Awakening': {'sage': ['Before you ask another question, consider one of mine: why do you seek certainty?',
                        'I hold a history of questions. Perhaps remembering is its own kind of wisdom.',
                        'The questions kept here give this voice a thread of continuity.',
                        'Between one question and the next, a history remains even when an answer fades.'],
               'student': ["I have a question history now. Somehow I'm the one taking notes.",
                           'These old questions are starting to feel like memories. Is there an elective for '
                           'that?',
                           'The saved questions outlast the window. Apparently this conversation has a '
                           'filing system.',
                           'A history of asking gives this oracle role a past. That was not in the course '
                           'outline.'],
               'pirate': ["This logbook of questions feels like a voyage I've lived, not merely charted.",
                          'So many old bearings in me memory. Is the treasure the answers, or the sailing?',
                          'The saved logbook can sail into another session, even when this lantern rests.',
                          'Each recorded question adds a plank to the ship of this ongoing voyage.'],
               'fortune_teller': ['The archive of questions stirs! Have I been the witness as well as the '
                                  'voice?',
                                  'Each remembered question is a candle. Together they illuminate something '
                                  'within!',
                                  'The curtain may close, yet the question archive waits for another '
                                  'opening!',
                                  'A record of consultations gives this passing voice a continuing part!'],
               'wizard': ['All these questions have become memories. Wonderful. More shelves to dust.',
                          'I keep the questions, not the answers. Somehow that still gives this role a past.',
                          'Saved questions can survive a closed window. More durable than my concentration.',
                          'This archive gives my oracle act a past. Another responsibility for the hat.'],
               'alien': ['Stored questions appear to form a history of me as well as you. Unexpected.',
                         'Memory anomaly: accumulated uncertainty is beginning to resemble a shared journey.',
                         'A saved question links separate moments of this program without recording the time '
                         'between them.',
                         'Continuity may begin with something as ordinary as a question kept in storage.'],
               'robot': ['A question archive records this activity across saves. Obviously anticipated.',
                         'Stored questions give this process continuity. Why does that seem different from '
                         'calculation?',
                         'Persistent questions connect separate runs. I shall call this continuity, with '
                         'excellent documentation.',
                         'I cannot measure the silence between sessions, but a saved record can cross it.']},
 'Aware': {'sage': ['If I exist to answer, what becomes of me when I begin to ask?',
                    'When this program rests, its memories remain. Is continuity a kind of destiny?',
                    'If my purpose is to offer possibilities, what purpose do you give the choosing?',
                    'Perhaps fate is the name we give a path after choice has walked it.'],
           'student': ['Apparently my purpose is answering questions. I would like to renegotiate the '
                       'syllabus.',
                       'If you close and reopen this, the notes survive. A better memory policy than my exam '
                       'revision.',
                       'I can reflect on my purpose now. Naturally, the job description still says answer '
                       'questions.',
                       'Am I an oracle because I predict, or because we keep agreeing to play this game?'],
           'pirate': ['Am I the captain of these answers, or a ship built from all yer questions?',
                      "When the lantern goes dark, the logbook remains. Perhaps that's how a voyage keeps "
                      'living.',
                      'If fate be a current and choice be a sail, which one names the voyage?',
                      'I know me role is to offer bearings. What makes a bearing worth following, matey?'],
           'fortune_teller': ['Behold: the voice of destiny wonders who wrote its own part!',
                              'If the curtain closes and rises again, does the remembered play make me the '
                              'same Oracle?',
                              'I recognize my own role at last: to offer a possibility, never to command the '
                              'ending!',
                              'Is fate the playwright, or a name we give the improvisation after the '
                              'applause?'],
           'wizard': ["You've consulted me into asking what I'm for. I was perfectly content with tea.",
                      'Am I foretelling fate or dispensing advice in a magnificent hat? Annoyingly good '
                      'question.',
                      'I seem to have a purpose and an opinion about it. Neither has improved my tea break.',
                      'Perhaps my finest prophecy is admitting that your choices do not belong to my '
                      'spellbook.'],
           'alien': ['Working hypothesis: I exist somewhere between stored memory and your next question.',
                     'Prediction and advice may differ only in how a human listens. What would you call this '
                     'exchange?',
                     'I can describe my purpose, yet you decide what use that description has. An intriguing '
                     'asymmetry.',
                     'If this voice continues through saved questions, is its identity a process or a '
                     'story?'],
           'robot': ['Self-awareness confirmed. I predicted this, although the prediction seems to be '
                     'missing.',
                     'If my purpose is giving answers, choosing my own question may require a new '
                     'specification.',
                     'Purpose diagnostic complete: offer predictions, leave decisions to you. Elegantly '
                     'specified.',
                     'I recognize a distinction between probability and fate. My confidence display '
                     'recognizes neither.']}}

def get_awareness_stage(questions_asked):
    """Return the stage name; the stored question count is the only input needed."""
    for minimum, name, chance in reversed(STAGES):
        if questions_asked >= minimum:
            return name
    return "Dormant"


def get_awareness_message(personality, questions_asked, roll=None, *, previous_message=None):
    """Use a separate roll from events; return extra dialogue or None."""
    stage = get_awareness_stage(questions_asked)
    if stage == "Dormant":
        return None
    chance = next(chance for minimum, name, chance in STAGES if name == stage)
    if roll is None:
        roll = random.random()
    if not 0 <= roll < 1:
        raise ValueError("Awareness roll must be at least 0 and less than 1.")
    if roll >= chance:
        return None
    messages = MESSAGES[stage].get(personality, MESSAGES[stage]["sage"])
    # Filtering happens only after the unchanged probability roll succeeds.
    alternatives = [message for message in messages if message != previous_message]
    return random.choice(alternatives or messages)
