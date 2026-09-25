# sc2-cheat-panel

[中文](README.md)

Playing the StarCraft II campaign the easy way: click a button, or press a hotkey in game, and the cheat is typed for you — no looking codes up, no typing them.

- All 23 official cheat codes, grouped, each with a (Traditional Chinese) description and where it works.
- The five most used have hotkeys out of the box (`Ctrl+Alt+1`–`5`); any cheat can be given one.
- The panel can stay on top; clicking a button switches back to the game before typing.
- No third-party packages: Python's own tkinter and the Windows API.

> ⚠️ **After any cheat, that campaign save earns no more achievements** (except the song easter egg, `OverEngineeredCodPiece`), until a new campaign is started or a save from before the first cheat is loaded. If you want achievements, do not use them.

## Compatibility

| Item | Version |
|---|---|
| OS | Windows 10 / 11, 64-bit (tested on Windows 10 Home 22H2, build 19045) |
| Python | 3.10 or newer (tested 3.12.10), with tkinter (included by the official installer) |
| StarCraft II | Tested with client 5.0.16 (build 97563). Cheats are part of the game and have not changed in years |

## Use

1. Double-click `Run.bat` (no console window).
2. Start a campaign mission. **Windowed (fullscreen) mode is recommended**: clicking the panel switches windows, which stutters or flashes black in exclusive fullscreen.
3. Either:
   - **Hotkey**: press it in game, e.g. `Ctrl+Alt+1` for god mode. The tool waits until Ctrl/Alt are released before typing.
   - **Button**: the tool switches to the game, presses Enter, types the code, presses Enter.
4. Click the `Ctrl+Alt+1` / 「＋設定熱鍵」 label beside a cheat to change its hotkey. At least two modifiers are required, because the game uses `Ctrl+<n>` for control groups and `Shift+<n>` to add to them.

### Default hotkeys

| Hotkey | Cheat | Effect |
|---|---|---|
| `Ctrl+Alt+1` | TerribleTerribleDamage | God mode (enter again to turn off) |
| `Ctrl+Alt+2` | WhoRunBartertown | +5000 minerals and gas |
| `Ctrl+Alt+3` | CatFoodForPrawnGuns | Fast build and upgrades |
| `Ctrl+Alt+4` | Bunker55AliveInside | No supply limit |
| `Ctrl+Alt+5` | TookTheRedPill | No fog of war |

The other 18 are one click away and can be given hotkeys. Instant defeat (`LetsJustBugOutAndCallItEven`) is click-only and asks first.

### Story-screen cheats

+5 million credits, all missions, all research, all cinematics and all news broadcasts are entered on the **ship / story screen**, not during a mission, and mainly apply to Wings of Liberty (credits and news do not work in Heart of the Swarm).

## Safety

- **Types into StarCraft II only**: for a hotkey, if the foreground window is not the game (say you are typing in a chat app), nothing is sent. The game is recognised by the process behind the window (`SC2_x64.exe`), not the title, so the Battle.net launcher and the map editor are never typed into.
- **Bypasses the input method**: characters are sent as Unicode by default, so a Zhuyin/Pinyin IME left on cannot turn a code into bopomofo. If the game ever ignores that, switch 「輸入方式」 to 「模擬實體按鍵」 (physical keys — affected by the IME, so switch it to English first).
- **No automation**: the tool enters official cheat codes and nothing else — no auto-macro, no auto-casting.

## Achievements without cheats

- **Slow the game down**: single-player allows a slower game speed (Options → Gameplay). Whether speed affects an achievement, the game will tell you.
- **Save mid-mission** before a big wave; reload that wave instead of the whole mission.
- **Read the mission first**: Liquipedia and similar sites cover each mission on Brutal — where attacks come from, when the big waves hit.
- **Split the goals**: take the mission-challenge achievements on a lower difficulty, then go for the Brutal clear on its own.

## Files

| File | Purpose |
|---|---|
| `app.py` | The panel |
| `cheats.py` | Cheat list and descriptions (sources at the top of the file) |
| `winput.py` | Finding and activating the game window, sending keys (Windows API via ctypes) |
| `hotkeys.py` | Global hotkeys (background thread) and hotkey rules |
| `config.py` | Reading and writing `settings.json` |
| `Run.bat` | Launcher without a console window |
| `tests/` | Unit tests: `python -m unittest discover -s tests` |
| `scripts/selftest.py` | Hands-on check without the game: really types into a text box and really fires a hotkey (takes focus for a few seconds) |

## Settings and undo

- Settings live in `settings.json` beside the program (hotkeys, always-on-top, input mode). **Delete it to return to defaults.**
- A broken settings file is renamed `settings.json.bad` and the program starts with defaults instead of failing to open.
- Nothing else is changed: no system settings, no registry, no game files. Closing the panel releases every hotkey.

## Moving to another PC

- **Install Python 3.10+ first**, ticking "Add python.exe to PATH". `Run.bat` says so if Python is missing.
- Copy the whole folder; bring `settings.json` along to keep your hotkeys.
- **If StarCraft II runs as administrator, run this tool as administrator too**, or Windows blocks the input (the panel says so).
- If another program (recording software, Discord…) already owns a hotkey, the panel lists which ones did not register; pick another combination.
- Windows only; the macOS version of StarCraft II is not supported.

## Known limits

- Cheat behaviour (e.g. "enter again to turn off") is the game's own; per-campaign support follows Blizzard's and the press's lists and was not tested mission by mission.
- In exclusive fullscreen, clicking a panel button may not switch smoothly; hotkeys are unaffected.
