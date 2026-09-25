"""settings.json next to the program: hotkeys, window and typing options.

A missing file means defaults. A broken one is kept as settings.json.bad and
replaced by defaults rather than stopping the program from starting — losing
custom hotkeys is annoying, a panel that will not open is worse.
"""

import json
import os
import shutil

from cheats import CHEATS, DEFAULT_HOTKEYS, by_code

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULTS = {
    "always_on_top": True,
    "input_mode": "unicode",  # or "scancode"; see winput.py
    "key_delay_ms": 15,
}


def defaults():
    return {**DEFAULTS, "hotkeys": {cheat.code: DEFAULT_HOTKEYS.get(cheat.code, "") for cheat in CHEATS}}


def load(path=DEFAULT_PATH):
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

    if isinstance(stored.get("always_on_top"), bool):
        settings["always_on_top"] = stored["always_on_top"]
    if stored.get("input_mode") in ("unicode", "scancode"):
        settings["input_mode"] = stored["input_mode"]
    delay = stored.get("key_delay_ms")
    if isinstance(delay, int) and 0 <= delay <= 200:
        settings["key_delay_ms"] = delay
    hotkeys = stored.get("hotkeys")
    if isinstance(hotkeys, dict):
        for code, hotkey in hotkeys.items():
            cheat = by_code(code)
            # Codes this version does not know are dropped, not kept around;
            # click-only cheats (instant defeat) never get a hotkey, even one
            # typed into the file by hand.
            if cheat is not None and not cheat.confirm and isinstance(hotkey, str):
                settings["hotkeys"][code] = hotkey
    return settings


def save(settings, path=DEFAULT_PATH):
    """Written to a temporary file first, so a crash mid-write cannot leave
    half a settings file behind."""
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)
