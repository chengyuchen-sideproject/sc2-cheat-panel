"""settings.json next to the program: hotkeys, window and typing options.

A missing file means defaults. A broken one is kept as settings.json.bad and
replaced by defaults rather than stopping the program from starting — losing
custom hotkeys is annoying, a panel that will not open is worse.
"""

import json
import os
import shutil

import hotkeys as hotkey_rules
from cheats import CHEATS, DEFAULT_HOTKEYS, by_code

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULTS = {
    "always_on_top": True,
    "input_mode": "unicode",  # or "scancode"; see winput.py
    "key_delay_ms": 15,
    # Shows the full panel / folds it back into the strip.
    "panel_hotkey": "Ctrl+Alt+0",
    # Where the folded strip sits, [x, y] in screen pixels; None = top centre.
    "strip_position": None,
    # Every cheat disabled and its hotkey released, so an achievement run
    # cannot be spoiled by a stray key. Remembered across restarts.
    "achievement_mode": False,
}


def defaults():
    return {**DEFAULTS, "hotkeys": {cheat.code: DEFAULT_HOTKEYS.get(cheat.code, "") for cheat in CHEATS}}


def load(path=None):
    # Looked up at call time, so the self-test can point it at a scratch file
    # and never touch the player's real settings.
    path = path or DEFAULT_PATH
    settings = defaults()
    if not os.path.exists(path):
        return settings
    try:
        with open(path, encoding="utf-8") as handle:
            stored = json.load(handle)
        if not isinstance(stored, dict):
            raise ValueError("not an object")
    except (OSError, ValueError):
        shutil.copyfile(path, path + ".bad")
        return settings

    for key in ("always_on_top", "achievement_mode"):
        if isinstance(stored.get(key), bool):
            settings[key] = stored[key]
    if stored.get("input_mode") in ("unicode", "scancode"):
        settings["input_mode"] = stored["input_mode"]
    delay = stored.get("key_delay_ms")
    if isinstance(delay, int) and 0 <= delay <= 200:
        settings["key_delay_ms"] = delay
    panel = stored.get("panel_hotkey")
    if isinstance(panel, str) and panel and hotkey_rules.problem(panel) is None:
        settings["panel_hotkey"] = panel
    position = stored.get("strip_position")
    if isinstance(position, list) and len(position) == 2 and all(isinstance(value, int) for value in position):
        settings["strip_position"] = position
    hotkeys = stored.get("hotkeys")
    if isinstance(hotkeys, dict):
        for code, hotkey in hotkeys.items():
            cheat = by_code(code)
            # Codes this version does not know are dropped, not kept around;
            # click-only cheats (instant defeat) never get a hotkey, even one
            # typed into the file by hand.
            if cheat is not None and not cheat.confirm and isinstance(hotkey, str):
                settings["hotkeys"][code] = hotkey
    # The panel's own hotkey wins over a cheat that was given the same one.
    for code, hotkey in settings["hotkeys"].items():
        if hotkey_rules.same(hotkey, settings["panel_hotkey"]):
            settings["hotkeys"][code] = ""
    return settings


def save(settings, path=None):
    """Written to a temporary file first, so a crash mid-write cannot leave
    half a settings file behind."""
    path = path or DEFAULT_PATH
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)
