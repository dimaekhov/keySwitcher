# KeySwitcher

KeySwitcher is a small Windows utility that watches typed words and switches between English and Russian keyboard layouts when it detects that a word was typed in the wrong layout.

The detector is context-aware: for every word it compares the actually typed text with the same physical keys interpreted in the other layout, scores both variants, and adds a sentence-level bias from recently accepted words. This helps cases such as `ghbdtn` -> `привет`, `руддщ` -> `hello`, and mixed sentences where short words need surrounding context.

It can also fix one simple typo pattern inside the current layout: two neighboring letters typed in the wrong order, for example `hlelo` -> `hello`. This is intentionally conservative and only triggers for strong common-word matches.

## Run

```bat
run.bat
```

or:

```powershell
python -m keyswitcher
```

Stop it with `Ctrl+C` in the console.

To add KeySwitcher to Windows startup for the current user:

```powershell
python -m keyswitcher --install-startup
```

To remove it from Windows startup:

```powershell
python -m keyswitcher --uninstall-startup
```

## Tray And Hint

When running, KeySwitcher adds an icon to the Windows notification area:

- `EN` means active with English as the current foreground layout.
- `RU` means active with Russian as the current foreground layout.
- `OFF` means KeySwitcher is paused.

Left-click the tray icon to pause or resume correction. Right-click it to open a small menu with pause/resume and exit actions.

After an automatic switch, KeySwitcher shows a short semi-transparent hint near the caret or mouse pointer with the target layout and corrected token.

The tray menu also includes `Edit rules...` and `Reload rules`. `Edit rules...` opens a small built-in window for both learned switching rules from `learning.local.json` and typo-protection exceptions from `exceptions.local.json`. Use `Reload rules` after saving to apply changes without restarting KeySwitcher.

The tray menu also includes `Show debug log`. It opens a small semi-transparent overlay in the corner of the screen with recent KeySwitcher log lines, color labels such as `OK`, `SKIP`, `ERR`, and `INFO`, and a draggable, resizable window frame so you can keep it visible while testing corrections in real time.

The same tray menu also lets you turn `Start with Windows` on or off without editing the registry manually.

## Manual Switch And Learning

Press `Del` to manually switch layouts:

- If you are in the middle of a word, `Del` converts that word to the opposite layout, switches the active layout, and blocks the normal delete action.
- If you already typed a word and delimiter, for example `руддщ `, pressing `Del` converts the previous token to `hello `.
- If there is no current or previous token, `Del` just toggles the foreground layout.

Select text and press `Shift+Del` to convert the selected text to the opposite layout. KeySwitcher detects the selected text script, replaces the selection in place, switches to the target layout, and blocks the normal Windows cut action.

Manual conversions are saved to `learning.local.json` when `learning_enabled` is true. The next time the same mistyped token appears, KeySwitcher applies the learned correction automatically.

KeySwitcher also fixes wrong-layout sentence punctuation in safe contexts. For example, in a Russian sentence, `&` typed from the English `Shift+7` key is replaced with `?`.

In plain language, KeySwitcher now tries to help with two different kinds of mistakes:

- You typed the right physical keys, but in the wrong keyboard layout.
- You stayed in the right layout, but accidentally swapped two neighboring letters in a common word.

## What Counts As A Word

KeySwitcher does not use a generic dictionary word boundary. Instead, it builds a "current token" while you type and decides whether each next character still belongs to the same word.

In plain language:

- Letters and digits stay inside the current word.
- Apostrophe `'` and hyphen `-` also stay inside the current word, but only after the word has already started.
- Space, `Enter`, and `Tab` end the current word.
- Separators such as `, ; : ) ] } "` also end the current word.
- Navigation keys such as arrows clear the current in-progress word, because the caret moved and the app can no longer safely continue the same token.

Sentence punctuation is handled a bit more carefully:

- `.`, `!`, and `?` usually end the current word.
- But if the same physical key would be a letter in the other keyboard layout, KeySwitcher may keep that character inside the token long enough to check whether the whole thing is actually a mistyped word in the wrong layout.

That is why some symbols may look surprising at first. For example, punctuation typed in one layout can still be treated as part of a mistyped word if it would have produced a letter in the other layout and the detector thinks the alternate-layout word is more plausible.

## Dry Run

To see decisions without modifying typed text:

```powershell
python -m keyswitcher --dry-run --verbose
```

## Build EXE

If you want a single executable, run:

```powershell
.\build.ps1
```

The script creates an isolated `.venv-build`, installs PyInstaller there, and writes `dist\KeySwitcher.exe`.

The packaged executable is built as a windowed tray app, so Windows startup does not open an extra console window.

If Windows Application Control blocks the unsigned executable, run the source version with `run.bat` or `python -m keyswitcher`.

## Configuration

Copy `config.example.json` to `config.local.json` and adjust thresholds if needed.

Important options:

- `auto_correct`: enables replacement of the last typed word.
- `dry_run`: logs corrections but does not type replacements.
- `min_word_chars`: minimum word length for correction.
- `score_margin`: how much better the alternate-layout candidate must be.
- `context_weight`: how strongly the current sentence affects decisions.
- `tray_icon`: shows the Windows tray icon.
- `switch_hint`: shows the semi-transparent switch hint.
- `hint_duration_ms`: controls how long the hint remains visible.
- `hint_opacity`: controls hint opacity from 80 to 255.
- `fix_capitalized_common_words`: lowercases known common words inside a sentence, for example `Работает` -> `работает`.
- `delete_switch_enabled`: enables the `Del` manual layout switch.
- `learning_enabled`: saves manual `Del` corrections and reuses them later.
- `learning_path`: path to the local learning JSON file.
- `typo_exceptions_path`: path to the local exceptions JSON file for protected words and suffixes.
- `fix_layout_punctuation`: fixes wrong-layout punctuation such as final `&` -> `?` in Russian context.
- `fix_transposed_letters`: fixes a single adjacent-letter swap in strong common-word cases, for example `hlelo` -> `hello`.
- `fix_repeated_consonants`: fixes accidental triple consonants in the current layout, for example `bookkkeeper` -> `bookkeeper`, unless the word or suffix is protected in the exceptions editor.

## How It Works

1. A global low-level Windows keyboard hook reads key presses.
2. For each key, WinAPI `ToUnicodeEx` calculates the character in the active layout and in the opposite layout.
3. The app stores the current word until a delimiter such as a space or punctuation.
4. The language detector scores the current-layout word and alternate-layout word using script, small dictionaries, common bigrams, vowels, suffixes, symbols, and sentence context.
5. If the alternate candidate is clearly better, the app backspaces the wrong word, types the corrected word as Unicode, and asks the foreground window to switch to the target layout.

## Notes

- The first version supports English and Russian layouts.
- Some elevated applications may ignore hooks from a non-elevated process. Run KeySwitcher with the same privilege level as the target app if needed.
- Password fields, terminals, code editors, and remote desktops can have special input behavior. Use `--dry-run` first if you want to tune thresholds safely.
