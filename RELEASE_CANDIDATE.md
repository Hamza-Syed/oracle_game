# The Oracle v1.0 release-candidate QA

Release verification update, 2026-09-14: the project owner confirms successful
manual source and packaged Windows verification. Packaged checks covered GUI
launch, personality selection, normal consultations, animations, conversational
responses, follow-ups, preference banter, self-evaluation, profanity reactions,
safety, and Stats/History/Achievements/Help. Save/reopen persistence works at
`%LOCALAPPDATA%\TheOracle\memory.json`. Windows packaging is complete, the MIT
License is selected, and all 253 automated tests pass. `VERSION` is `1.0.0`.

The report below preserves the original 2026-09-12 audit as historical evidence;
its pending manual-check, packaging, versioning, and Git observations describe
that earlier state and are superseded by this update.

Audit date: 2026-09-12. Recommendation: **READY WITH MINOR CAVEATS**.

The automated and scripted checks found no release-blocking gameplay defect.
Complete a physical desktop visual/keyboard check before labeling the release
v1.0.0. No version constant or packaging metadata exists, and no tag was created.

## Baseline and final verification

- Initial suite: **245 tests passed**, no reported warnings or skips.
- Final suite: **248 tests passed**, no reported warnings or skips. All original
  245 tests remain and pass.
- Command: `python -m unittest discover -s tests -q`.
- Environment: Windows, Python 3.14.5, Tcl/Tk 8.6.15.
- Both `main.py` and `gui.py` imported successfully.
- Production modules, dialogue tables, frontend callbacks, persistence code,
  and the existing test modules were reviewed. No unfinished required TODOs,
  debugging hooks, experimental branches, or release-blocking unused imports
  were found. Production random selection remains unseeded.

## Exact changes and issues addressed

| File | Issue and change |
| --- | --- |
| `README.md` | Added the Python requirement and tested version; documented colorful-language reactions, their result kind and context behavior; made the single-instance save rule visible in player instructions. |
| `.gitignore` | Existing rules missed randomly named atomic-save temporary files and corrupt-save backups. Added the actual generated filename patterns. |
| `tests/test_release_candidate.py` | Added three release integration tests for foreign-working-directory launch, sequential frontend save sharing, and real Tk timers/lifecycle. |
| `tests/test_gui_layout.py` | Extended the existing long-content test to cover awareness and event roles, multiple ordered messages, save errors, and achievement banners. |
| `RELEASE_CANDIDATE.md` | Added this audit record and remaining checks. |

No production Python code, gameplay, save schema, safety rules, animation timing,
or layout was changed. No dependency, feature, versioning system, or package was added.

## Results

| Area | Evidence and result |
| --- | --- |
| Fresh user | A real terminal subprocess launched an isolated source copy with no save, selected a personality, answered a question, unlocked First Question, and created a save. A separate fresh hidden-Tk session verified all seven selector entries and first-question saving. |
| Sequential frontends | A hidden GUI created progress, closed, the terminal loaded and extended that same save, then another GUI loaded the result. No simultaneous frontend ownership of a save. |
| Existing users | Existing tests cover oldest/current formats and each missing or invalid field. Additional isolated smoke checks confirmed old, partial, malformed, empty, and invalid-UTF-8 saves remain playable and reload after another question. |
| Save/reload | Counts, original history wording, normalized repeats, achievements, and personality usage survive. Existing tests exercise all achievement thresholds and cross-session discoveries. Follow-up context/depth, awareness anti-repeat state, switch counters, and GUI state remain session-only. |
| Commands | Engine/terminal tests cover all commands with case/whitespace variations and unchanged question progress. Hidden-Tk integration exercised typed display commands and repeated secondary-window destruction/reopening, plus typed quit. Existing callback tests cover typed change. |
| Personalities | All seven have selection/statistics coverage and complete response, topic, reflective, preference, follow-up, profanity, and awareness data. Normal pools retain five positive, four uncertain, and three negative distinct answers. No ordinary response was found to declare personal hopelessness or insult the player. |
| Conversation | Existing deterministic tests cover acknowledgments, self-evaluation, preferences, follow-ups, profanity reactions, and longer-input false positives. Neutral reactions bypass progress and entertainment; real consultations count and save normally. Follow-up allowance and reset/preservation rules remain intact. |
| Discoveries | Existing tests exercise every Easter egg, exact achievement boundaries, unlock-once behavior, persistent awards, and hidden locked metadata. No discovery triggers or secret conditions were added to player documentation. |
| Events/awareness | Existing deterministic tests cover all event tiers/variants and probability boundaries, answer replacement, awareness stages and probability boundaries, four-line pools, immediate-repeat prevention, session-only state, and suppression rules. No probabilities or thresholds changed. |
| Safety | All existing classifier and integration regressions pass: concerning intent, ambiguity, benign academic/fictional context, negation, and profanity-containing disclosures. Guidance bypasses entertainment, clears follow-up context, remains scrollable, and does not enter progress or saves. Rules and wording are unchanged. |
| Terminal | Scripted session covered selection, ordinary consultation, acknowledgment, follow-up, preference, self-evaluation, profanity reaction, all display commands, change, and quit. Output was checked through captured text. Windows cp1252 output exercised the trophy fallback and accented achievement names without an exception. |
| GUI | Hidden real-Tk checks passed for construction, selection, actual timer-driven reveals, duplicate submission blocking, control restoration, immediate replies, banner preservation/expiry, information windows, closing during animation, and typed quit. Existing callback tests cover focus restoration, safety cancellation, stale callbacks, save-error display, and the unchanged 900 ms sequence. |
| Layout/long content | Real widgets passed default 900×780, larger 1000×900, and minimum 740×700 checks. The response retains at least 150 px in the tested layouts, grows with the window, and keeps input/buttons accessible. Wrapped long answers, awareness, events, safety, ordered messages, save errors, and banners retain complete scrollable text. |
| Save failures | Existing tests simulate partial temp writes, sync failure, and replacement failure; previous saves survive. Engine/frontend tests retain the answer and session progress, show an error, and retry on the next question. Recovery backup failure stops startup and preserves the original. |
| Paths | A copied terminal entry point ran by absolute path from a different directory and saved beside its copied modules, not the working directory. Both entry points imported from that foreign directory. The user's real save was not used for smoke tests. |
| Unicode | Existing UTF-8/BOM, Unicode question/achievement round-trip, malformed Unicode recovery, and case-folding tests pass; the additional cp1252 trophy fallback smoke passed. |

## Repository and documentation

This workspace has no `.git` directory, so tracked-file history could not be
audited. The local `memory.json` is already explicitly ignored and was neither
deleted nor edited. Local `__pycache__` directories are ignored. No virtual
environment, packaging output, or abandoned save artifacts were found in the
project inventory. Backup/temporary-save ignore rules now match generated names.
Ignore rules affect future tracking; they would not untrack files in another checkout.

README accurately describes both entry points, shared engine, core features,
save/recovery behavior, high-level safety limitations, and the test command.
It did not maintain a test count, so none was introduced there. No secret triggers,
secret conditions, safety patterns, or probability tables were disclosed.

## Remaining checks and limitations

- No physical visual, mouse, or keyboard verification was performed. Hidden
  real widgets and automated callbacks do not establish aesthetic quality,
  actual desktop focus behavior, high-DPI appearance, or accessibility.
  Complete the README manual checklist on the intended release desktop.
- Only this Windows/Python 3.14.5/Tk 8.6.15 environment was exercised. Python
  3.10 is the code's minimum language requirement, not a separately tested runtime.
  Other operating systems, fonts, terminal encodings, and display scales remain unverified.
- Tkinter and a graphical desktop are required for the GUI. Tiny window sizes
  below the configured minimum are intentionally unsupported.
- Saves assume one active process and a writable game directory. Atomic replacement
  does not merge sessions. Unsaved progress can be lost when closing after a save failure.
- Safety is an offline pattern check, with possible false positives and missed
  intent; it is not clinical assessment. This audit verified the existing behavior,
  not universal detection.
- No executable packaging, signing, installer, version metadata, or Git tag was
  created; these were outside this QA request.

Subject to the manual desktop check and acceptance of these documented limits,
the code is a suitable candidate for the v1.0.0 label.
