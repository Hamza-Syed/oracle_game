# The Oracle

A Python game with terminal and graphical frontends, personality, persistent memory, and discoveries.
Requires Python 3.10 or newer; release checks currently run on Python 3.14.
No third-party Python packages are required. The GUI also needs Tkinter.

Run the terminal version from this folder:

```powershell
python main.py
```

Or launch the graphical version:

```powershell
python gui.py
```

The GUI uses Tkinter, included with standard Python installations on most systems,
and requires a graphical desktop. It needs no images, internet access, or additional
Python packages. Both frontends use the same engine and save file.

Choose a personality in the startup window, then type a question and press Enter
or **Ask the Oracle**. The ball briefly shakes during “Consulting the Oracle...”
before revealing the response. Buttons open Stats, History, Achievements, and Help;
typed commands also work. Responses wrap and scroll, showing only the latest consultation.
Achievement unlocks appear together in a temporary banner. Safety guidance appears immediately
plainly with the ball hidden. Closing the window exits without adding a question.

Choose a personality, then ask questions:

1. **Wise Sage**: calm, thoughtful guidance.
2. **Sarcastic Student**: dry jokes about studying and procrastination.
3. **Pirate**: nautical predictions from a weathered captain.
4. **Dramatic Fortune Teller**: theatrical prophecies about destiny.
5. **Grumpy Wizard**: ancient wisdom with playful impatience.
6. **Alien Oracle**: curious observations about humans and their strange rituals.
7. **Overconfident Robot**: supposedly flawless calculations with comical certainty.

Each personality has 12 normal answers mixing positive, negative, and uncertain
predictions, plus its own exam, job, and internship reactions. Use `change` to
switch to any personality during a session.

Occasionally the Oracle may hesitate, behave unusually, or offer a surprising
reply instead of a prediction. Some moments are much rarer than others; discover
them as you play. Your question still counts and is saved, whatever the reply.
The Oracle's behavior may gradually change the more you consult it, sometimes
offering a reflection alongside its answer. Especially unusual events get the
moment to themselves. Use `stats` to see its current awareness stage.
Reflections have several variations for each personality and stage. Within a
session, the same personality/stage avoids repeating its last reflection.
The Oracle contains hidden achievements and Easter eggs for curious players to discover.

Commands:

- `change`: choose a different personality.
- `help`: list all commands and their explanations.
- `stats`: see lifetime, unique, and repeated question counts, current personality,
  awareness stage, unlocked achievement count, normal achievement total, and favorite topic.
- `history`: see the latest 10 actual questions, oldest to newest in that selection.
- `achievements`: see unlocked and locked achievements.
- `quit`: exit.

The Oracle recognizes exam, job, and internship topics, responds in character,
and notices repeated questions regardless of capitalization or extra whitespace.
Blank input and commands do not count as questions.
The Oracle also responds briefly to a few simple acknowledgments, thanks,
laughter, and dismissals. These do not count as questions or advance progress,
and appear immediately in the GUI. Longer questions containing those words
still receive normal consultations.
For a small set of direct questions about intelligence, appearance, or personal
worth, the Oracle gives an in-character reflection instead of a random yes/no
judgment. These remain real questions for history and progression.
When asked about its own preferences, the Oracle can also offer playful
in-character banter instead of a fortune. These consultations count normally.
After an Oracle reply, a few short reactions can prompt an immediate in-character
follow-up without adding a question or advancing progress. Each consultation
allows up to two reactions; after that, the Oracle asks for a new question.
The Oracle may also react in character to standalone colorful language. These
reactions appear immediately, do not advance progress, and preserve any remaining
follow-up allowance.
Commands ignore capitalization and surrounding whitespace. Repeated questions
count each asking after the first: asking one question five times adds four
repeats. History display never removes questions from your save. Locked secret
achievements appear as `???`; their names and descriptions appear after unlocking.

Memory and achievements save after each question in `memory.json` beside the
game. A new game starts with empty memory only when no save exists; an existing
save restores your progress. Keep a backup of `memory.json` to preserve it.
Run only one game instance at a time; close the terminal or GUI before opening
the other. Both use the same save, even when launched from another folder.
If saving fails, progress stays in the current session and the next question
retries saving; closing before a successful save loses unsaved progress.

Achievements unlock at 1, 10, and 100 total questions, and at 5 repetitions of
one question. The Oracle's growing awareness is playful, fictional character dialogue.

## Safety override

The Oracle breaks character when its local safety check detects potentially
dangerous intent or concerning ambiguity. It offers a serious check-in or
crisis guidance instead of entertainment. Flagged input is not added to game
memory, history, counts, or achievements, and no safety log is written.
This offline, pattern-based check can miss intent or misread context; it is not
a clinical assessment or a substitute for human support or emergency services.

## Files

- `main.py`: terminal menus, input, result rendering, and exit handling.
- `gui.py`: Tkinter window, Canvas ball, personality selector, and result/data displays.
- `game.py`: shared gameplay orchestration through `OracleGame`.
- `commands.py`: read-only command data and terminal display formatting.
- `personalities.py`: random answers and topic reactions.
- `memories.py`: question history, topic detection, and JSON storage.
- `memory.py`: an alias so either tutorial import spelling works.
- `achievements.py`: achievement rules using persistent memory.
- `random_events.py`: occasional special events and their dialogue.
- `self_awareness.py`: progression stages and occasional reflections.
- `easter_eggs.py`: special phrase responses.
- `safety.py`: local safety assessment and serious responses.

Saves persist between sessions, and older formats remain supported. Damaged
fields are recovered where possible while keeping valid data. Unreadable saves
are backed up beside the game before starting fresh; if backup fails, the game
leaves the original alone and reports the problem. Saving replaces the previous
file only after the new file has been fully written.

Run the automated checks:

```powershell
python -m unittest discover -s tests -v
```

## Development: shared engine

`OracleGame` in `game.py` owns one session's selected personality, `Memory`, and
`AchievementTracker`. It coordinates the existing specialist modules and never
calls `input()` or `print()`. `main.py` is the terminal frontend and `gui.py` is the
Tkinter frontend. Both call the same engine; GUI widgets stay outside it.

```python
from game import OracleGame
from memories import Memory

game = OracleGame(Memory("example-memory.json"))
choices = game.get_personalities()  # {personality_id: display_name}
selection = game.select_personality("sage")
result = game.process_input("Will I pass my exam?")
stats = game.get_stats()           # No simulated command or terminal parsing
```

Public methods:

- `get_personalities()`: a copy of the seven IDs and display names.
- `select_personality(id)`: selects or switches, returning a `GameResult`.
  Invalid IDs leave the current selection and progress unchanged.
- `process_input(text)`: handles exact commands, blank input, safety, narrow conversational input, and gameplay.
- `get_help()`: a command-to-explanation dictionary.
- `get_stats()`: a snapshot with `questions_asked`, `unique_questions`,
  `repeated_questions`, `personality_id`, `personality_name`, `awareness_stage`,
  `achievements_unlocked`, `normal_achievements`, and `favorite_topic`.
- `get_history()`: the latest ten `{number, question}` entries, oldest first.
- `get_achievements()`: `{name, description, unlocked}` entries. Locked secret
  entries have `None` for name and description, so an interface cannot reveal them
  accidentally by displaying this data.

`GameResult` contains:

| Field | Meaning |
| --- | --- |
| `kind` | `question`, `conversation`, `follow_up`, `vulgar_reaction`, `self_evaluation`, `preference`, `safety`, `easter_egg`, `event`, `blank`, a display command name, `quit`, `select_personality`, `personality_selected`, or `invalid_selection` |
| `messages` | Ordered `Message(role, text)` objects, without terminal headers or trophy formatting |
| `new_achievements` | Names newly unlocked by this operation |
| `data` | A display-command snapshot, event metadata, or `None` |
| `save_error` | An error string if this operation could not save, otherwise `None` |

Message roles distinguish `topic`, `repeat_notice`, `repeat`, `achievement`,
`answer`, `event`, `awareness`, `easter_egg`, `safety`, `notice`, and `error`.
Render them in order. Achievement messages contain the name; `new_achievements`
exposes the same unlocks for UI state, so do not render a second notification for
that list. Event metadata retains `message`, `rarity`, and `show_normal_answer`.
Safety results contain guidance, not the submitted sensitive text.

The frontend handles `quit` and `select_personality`; these results do not close
the process or open a menu themselves. A new engine starts without a personality.
Before selection, an ordinary question requests selection without recording it;
safety assessment still applies. For a new session, construct a new engine with
a newly loaded `Memory`, preserving the existing session-boundary behavior.

Startup load errors propagate to the frontend. Save failures return `save_error`
and messages while preserving session progress for the next save attempt.
Gameplay hooks can be mocked in `game`, and the existing achievement clock remains
mockable in `achievements`; production randomness is not seeded.
Awareness selection keeps only the last line per personality/stage in `OracleGame`.
It does not scan history or add save fields. The normal trigger roll runs first;
only a successful roll excludes the previous line from selection.

Follow-up context is also session-only: an eligible personality ID and a reaction
counter, with no stored answer text or extra question copy. Normal answers,
reflective replies, preference banter, and Easter eggs qualify; events qualify
only when accompanied by a normal answer. Replacement events alone do not.
New consultations clear and then replace context if eligible. Actual personality
changes, safety, quitting, and restarting clear it. Selecting the same personality,
display commands, blanks, conversational acknowledgments, and vulgar reactions preserve it without
extending the two-reaction limit. A recognized reaction without context asks for
a new consultation and remains progression-neutral. GUI follow-ups leave existing
achievement banners and their timers alone.

The save file assumes one active process. Simultaneous independent processes may
overwrite each other's newer progress; atomic saving prevents partial files but
does not merge separate sessions.

## Development: GUI checks

`tests/test_gui.py` exercises the thin GUI callbacks and render preparation with
widget doubles, so those tests do not require a display server. It covers direct
engine calls, submission guarding, ordered messages, safety styling, secret
visibility, save errors, dialog focus, and clean shutdown. Additional checks cover
delayed reveals, control restoration, stale callback guards, banner replacement,
safety cancellation, personality accents, and secondary-window reuse.

Animation state stays in `gui.py`: a 900 ms sequence uses `after()` callbacks and
redraws around a fixed center. Presentation tokens guard against stale callbacks;
closing or a safety result cancels the reveal. The engine processes and saves the
question before the visual delay, so closing during a reveal does not undo progress.
Personality changes wait until the reveal finishes. Banners expire after five seconds.

A scripted check with hidden real Tk 8.6 widgets also verified construction,
personality selection/switching, Ask button callbacks, Return binding registration,
all four information windows, special replies, achievement display, safety text,
and closing. A further hidden-window check exercised real timer-driven reveals,
event-loop responsiveness, banner expiry, safety cancellation, window reuse,
three window geometries, and closing mid-animation without callback errors.
This does not replace visual or keyboard smoke testing.

Manual desktop checklist for this first GUI:

- Launch `python gui.py`; check layout at the default and minimum window sizes.
- Check ball depth and centering, subtle shake, consultation text, and delayed reveal.
- Resize during a reveal; check the ball returns to center and the UI stays responsive.
- Check that all seven personalities appear and question controls require selection.
- Submit with Enter and Ask; verify one question per submission and a cleared entry.
- Repeatedly press Enter/Ask during the reveal; check no duplicate question and restored focus afterward.
- Change personality, including selecting the current one.
- Check the current-personality label and small accent update without changing the overall design.
- Open Stats, History, Achievements, and Help through both buttons and typed commands.
- Check ordinary and special replies, achievement notifications, and long response scrolling.
- Check grouped achievement banners disappear, event emphasis is subtle, and reflections are readable in italics.
- Check that safety guidance stays readable, preserves its wording, and hides the ball.
- Verify safety has no entertainment delay or banner, and save warnings do not hide responses.
- Close with the window control and with typed `quit`.
- Close during the shake and check no delayed callback errors appear.
- Run `python main.py` to check the terminal frontend independently.
