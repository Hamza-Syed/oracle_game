# The Oracle v1.0.0

The Oracle is a playful Python Magic 8 Ball game that grew into a personality-driven
interactive experience. Ask a question, choose a voice, and return to an Oracle
that remembers your consultations and has a few surprises waiting.

## Highlights

- **Seven distinct personalities** with their own fortunes, topic reactions, and conversational style.
- **Animated Tkinter GUI** with a shaking Magic 8 Ball, scrollable responses, and achievement banners.
- **Terminal interface** for the same game through a simple question prompt.
- **Persistent memory** with question history, repeat tracking, statistics, and achievements across sessions.
- **Hidden secrets and rare events** for curious players to discover.
- **Evolving self-awareness** through fictional reflections as you keep playing.
- **Conversational reactions and follow-ups**, including acknowledgments, preference banter,
  reflective self-evaluation replies, and playful responses to colorful language.
- **Safety override** that steps out of character when serious guidance is more appropriate.
- **Robust persistence** with atomic saves, corruption recovery, and support for older save formats.

## Personalities

- **Wise Sage** — calm, thoughtful, and quietly amused.
- **Sarcastic Student** — dry humor with an academic streak.
- **Pirate** — nautical predictions and weathered wisdom.
- **Dramatic Fortune Teller** — theatrical visions of destiny.
- **Grumpy Wizard** — magical advice with playful impatience.
- **Alien Oracle** — curious observations of human behavior.
- **Overconfident Robot** — elaborate certainty and comically confident calculations.

## Safety

The Oracle breaks character for potentially dangerous self-harm or violence-related
input and provides serious safety guidance. These interactions bypass playful
presentation and are not recorded in game history or progress.

## Technical Highlights

- Modular Python architecture with a shared `OracleGame` engine for both frontends.
- Tkinter GUI and standard-library JSON persistence; no third-party runtime packages.
- Atomic save writing, corruption backups, and backward-compatible loading.
- UTF-8 storage for questions and achievements.
- **253 passing automated tests**, including five packaged-save-path tests.
- Completed release-candidate QA and owner-confirmed manual source and packaged Windows verification,
  including safety and save/reopen persistence.

## Windows Build

The Windows x64 packaged version is available as a release attachment:

1. Download `TheOracle-v1.0.0-Windows.zip`.
2. Extract the entire ZIP.
3. Launch `TheOracle.exe` inside the extracted folder.

No Python installation is required.
Keep the accompanying `_internal` folder intact.
Saves use `%LOCALAPPDATA%\TheOracle\memory.json`, with
`~/AppData/Local/TheOracle/memory.json` as the fallback. Source saves are not copied.
The executable is unsigned. No SmartScreen or Defender warning was observed during
the local launch, but other Windows systems may show reputation warnings.
Manual verification confirmed personality selection, normal consultations and animations,
conversational responses, contextual follow-ups, preference banter, self-evaluation,
playful profanity reactions, safety behavior, and Stats/History/Achievements/Help.
Closing and reopening preserved progress in the packaged save location.

## License

The Oracle is released under the MIT License, copyright 2026 Hamza Syed.

## Running From Source

Use Python 3.10 or newer and run these commands from the project folder.
The GUI also requires Tkinter and a graphical desktop. Verification used Python 3.14 on Windows.

Terminal:

```sh
python main.py
```

GUI:

```sh
python gui.py
```

Type `help` at the question prompt to see the available commands.
Both interfaces use `memory.json` beside the game; close one before starting the other.

## Known Limitations

- Saves assume one active Oracle process at a time.
- Safety classification uses local heuristics and cannot perfectly interpret every possible indirect phrase.
- v1.0 has been primarily tested on Windows.
