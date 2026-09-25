"""Global hotkeys: "Ctrl+Alt+1" pressed anywhere, even inside the game.

RegisterHotKey delivers WM_HOTKEY to the thread that registered it, so a
background thread owns the registrations and runs its own message loop.
Changing the set is a message to that thread; it unregisters everything and
registers the new set itself.

Parsing and validation are plain functions, tested without Windows.
"""

import sys
import threading

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000

MODIFIERS = {"Ctrl": MOD_CONTROL, "Alt": MOD_ALT, "Shift": MOD_SHIFT}
MODIFIER_ORDER = ["Ctrl", "Alt", "Shift"]

# Keys offered in the picker, with their virtual-key codes.
KEYS = {
    **{str(digit): 0x30 + digit for digit in range(10)},
    **{chr(code): code for code in range(ord("A"), ord("Z") + 1)},
    **{f"F{n}": 0x6F + n for n in range(1, 13)},
}


def parse(text):
    """'Ctrl+Alt+1' -> (modifier flags, virtual key). Raises ValueError."""
    parts = [part.strip() for part in str(text).split("+") if part.strip()]
    if not parts:
        raise ValueError("empty hotkey")
    *mods, key = parts
    flags = 0
    for mod in mods:
        normalised = mod.capitalize()
        if normalised not in MODIFIERS:
            raise ValueError(f"unknown modifier: {mod}")
        flags |= MODIFIERS[normalised]
    key = key.upper()
    if key not in KEYS:
        raise ValueError(f"unknown key: {key}")
    return flags, KEYS[key]


def format_hotkey(mods, key):
    """(['Alt', 'Ctrl'], '1') -> 'Ctrl+Alt+1', modifiers in a fixed order."""
    ordered = [mod for mod in MODIFIER_ORDER if mod in mods]
    return "+".join([*ordered, key.upper()])


def problem(text):
    """Why this hotkey is a bad idea in StarCraft II, or None if it is fine.

    At least two modifiers: a bare key, Ctrl+<n> (control groups), Shift+<n>
    (adding to a group) and Alt+<n> are all things the game or the player
    already uses, and a registered hotkey swallows the key before the game
    sees it.
    """
    try:
        flags, _ = parse(text)
    except ValueError as error:
        return f"看不懂這個組合（{error}）"
    count = sum(1 for flag in MODIFIERS.values() if flags & flag)
    if count < 2:
        return "至少要按住兩個修飾鍵（例如 Ctrl+Alt），不然會搶走遊戲本身的按鍵"
    return None


def same(first, second):
    """True when two hotkey strings are the same combination. Anything that
    does not parse (a hand-edited settings file) matches nothing."""
    try:
        return bool(first) and bool(second) and parse(first) == parse(second)
    except ValueError:
        return False


def conflicts(assignments):
    """{code: hotkey} -> {hotkey: [codes]} for hotkeys used more than once."""
    seen = {}
    for code, hotkey in assignments.items():
        if not hotkey:
            continue
        try:
            key = parse(hotkey)
        except ValueError:
            continue
        seen.setdefault(key, []).append(code)
    return {format_from(key): codes for key, codes in seen.items() if len(codes) > 1}


def format_from(parsed):
    flags, vk = parsed
    mods = [name for name in MODIFIER_ORDER if flags & MODIFIERS[name]]
    key = next(name for name, code in KEYS.items() if code == vk)
    return format_hotkey(mods, key)


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012
    WM_APP_RELOAD = 0x8000 + 1

    user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
    user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
    user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    class HotkeyThread(threading.Thread):
        """Owns the registrations. `on_press(code)` and `on_failed([hotkeys])`
        are called from this thread; the UI hands them to its own loop."""

        def __init__(self, on_press, on_failed):
            super().__init__(daemon=True, name="hotkeys")
            self.on_press = on_press
            self.on_failed = on_failed
            self._wanted = {}
            self._active = {}
            self._lock = threading.Lock()
            self._ready = threading.Event()
            self._thread_id = None

        def set_hotkeys(self, assignments):
            """{code: 'Ctrl+Alt+1' or ''} — applied on the hotkey thread."""
            with self._lock:
                self._wanted = dict(assignments)
            self._ready.wait(2)
            if self._thread_id:
                user32.PostThreadMessageW(self._thread_id, WM_APP_RELOAD, 0, 0)

        def stop(self):
            if self._thread_id:
                user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

        def run(self):
            self._thread_id = kernel32.GetCurrentThreadId()
            msg = wintypes.MSG()
            # Any call to GetMessage/PeekMessage creates the queue; after this
            # PostThreadMessage from other threads cannot be lost.
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
            self._ready.set()
            self._reload()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    code = self._active.get(msg.wParam)
                    if code:
                        self.on_press(code)
                elif msg.message == WM_APP_RELOAD:
                    self._reload()
            self._unregister_all()

        def _unregister_all(self):
            for hotkey_id in list(self._active):
                user32.UnregisterHotKey(None, hotkey_id)
            self._active = {}

        def _reload(self):
            self._unregister_all()
            with self._lock:
                wanted = dict(self._wanted)
            failed = []
            for index, (code, text) in enumerate(sorted(wanted.items()), start=1):
                if not text:
                    continue
                try:
                    flags, vk = parse(text)
                except ValueError:
                    failed.append(text)
                    continue
                if user32.RegisterHotKey(None, index, flags | MOD_NOREPEAT, vk):
                    self._active[index] = code
                else:
                    # Usually another program already owns this combination.
                    failed.append(text)
            if failed:
                self.on_failed(failed)
