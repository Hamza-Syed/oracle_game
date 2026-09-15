# Changelog

Notable changes to The Oracle are recorded here.

## [1.0.0] - 2026-09-14

### Added

- MIT License (copyright 2026 Hamza Syed).
- Windows one-folder build configuration, release ZIP/checksum script, and real GUI screenshots.
- Persistent per-user saves for packaged Windows runs; source-mode save location unchanged.
- Classic Magic 8 Ball gameplay with seven distinct Oracle personalities.
- Terminal interface and Tkinter GUI with animated consultations and achievement banners.
- Persistent memory, question history, repeat tracking, and player commands.
- Normal and secret achievements, Easter eggs, and random Oracle events.
- Evolving fictional self-awareness and contextual follow-up reactions.
- Conversational acknowledgments, personality preference banter, self-evaluation handling,
  and playful profanity reactions.
- Safety override for concerning self-harm and harm-to-others language.
- Atomic save writing, corruption recovery, and backward-compatible saves.

### Quality

- Modular architecture with a shared, frontend-independent `OracleGame` engine.
- Extensive deterministic automated testing and completed release-candidate QA.
- Manual source and packaged Windows GUI verification completed by the project owner,
  including safety and persistent packaged saves; 253 automated tests pass.
- UTF-8 persistence and documented single-process save ownership.
