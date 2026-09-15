# Developer notes

Run commands from the project root.

## Windows distribution

The 2026-09-14 local build used Windows x64, Python **3.14.5**, and
PyInstaller **6.22.3**. Build dependencies are pinned in `requirements-build.txt`
and are not game runtime dependencies. With Python 3.14.5 x64 installed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean TheOracle.spec
.\.venv\Scripts\python.exe scripts/package_windows.py
```

`TheOracle.spec` builds `gui.py` as a windowed executable, with no console,
into `dist/TheOracle/TheOracle.exe`. One-folder mode keeps the bundled Python
and Tcl/Tk runtime intact and avoids one-file startup extraction. Do not remove
files from `_internal`. No terminal executable is built. No custom icon exists;
the default is used. The configuration is repeatable, but binary-identical ZIPs
are not guaranteed across rebuilds or dependency/platform changes.

The packaging script uses `VERSION` to create
`dist/TheOracle-v1.0.0-Windows.zip` and its `.sha256` file. The archive extracts
into `TheOracle-v1.0.0-Windows/`. It rejects save files, corrupt-save backups,
tests, virtual environments, and common developer metadata. Build outputs remain
ignored; the spec and scripts belong in source history and binaries in release assets.

`memories.default_memory_path()` preserves source saves beside `memories.py`.
Frozen runs use `%LOCALAPPDATA%/TheOracle/memory.json`, falling back to
`Path.home()/AppData/Local/TheOracle/memory.json`. The parent is created before
loading. Explicit `Memory(path)` values override both defaults. No save migration
or schema change occurs. The five tests in `tests/test_packaged_paths.py` isolate
environment variables and temporary directories, including directory-creation
failure and avoiding `_MEIPASS`.

### Local build validation (2026-09-14)

- Baseline: 248 tests; after the persistence change: 253 tests passing.
- Built executable launched on Windows and displayed all seven personalities;
  selecting Wise Sage worked. No console or security warning was observed.
- The launch used an isolated `LOCALAPPDATA` under
  `build/packaged-smoke-profile`, leaving the source save untouched.
- The project owner subsequently completed manual packaged verification: launch,
  personality selection, consultations and animations, conversational responses,
  follow-ups, preference banter, self-evaluation, profanity reactions, safety,
  and Stats/History/Achievements/Help all work. Save/reopen persistence was confirmed
  at `%LOCALAPPDATA%\TheOracle\memory.json`. This completes the checks that desktop
  control errors had prevented during the initial automated build session.
- PyInstaller reported optional platform-module warnings; the built GUI launched
  without an import error. The executable is unsigned. The owner selected the
  MIT License, recorded in the root `LICENSE` file.

For future releases, repeat the GUI checklist below against the executable,
including safety non-persistence and save/reopen checks. The v1.0.0 packaged
manual verification is complete and publication has been authorized by the owner.

## Shared engine

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
