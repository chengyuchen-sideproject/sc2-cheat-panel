"""Typing a cheat into StarCraft II through the Windows input queue.

Only standard Win32 calls through ctypes: no third-party packages.

How a cheat is entered in game: Enter opens the chat box, the code is typed,
Enter sends it. This module builds that sequence (a pure function, tested
without a game) and plays it with SendInput.

Two ways of typing letters:
  - "unicode": KEYEVENTF_UNICODE. The character is delivered as-is and never
    passes through the input method, so a Zhuyin/Pinyin IME left switched on
    cannot turn "SpectralTiger" into bopomofo. Default.
  - "scancode": physical key presses, lower-cased (cheats are not case
    sensitive). A fallback for games that ignore synthetic Unicode input; it
    *is* affected by an active IME.
"""

import os
import sys
import time

GAME_EXES = {"sc2_x64.exe", "sc2.exe"}

VK_RETURN = 0x0D
SCAN_RETURN = 0x1C
MODIFIER_VKS = (0x10, 0x11, 0x12, 0x5B, 0x5C)  # Shift, Ctrl, Alt, left/right Win

# Pauses, in seconds. The chat box needs a moment to open before it takes
# characters; everything else is a small gap so no key is dropped.
CHAT_OPEN_DELAY = 0.12
AFTER_ACTIVATE_DELAY = 0.25


def build_sequence(code, mode="unicode"):
    """The key events for one cheat: [(kind, value, key_up), ...].

    kind is "scan" (a physical key by scan code) or "unicode" (a character).
    Enter is always a physical key: the chat box opens on a real Enter.
    """
    if mode not in ("unicode", "scancode"):
        raise ValueError(f"unknown input mode: {mode}")
    events = [("scan", SCAN_RETURN, False), ("scan", SCAN_RETURN, True), ("pause", CHAT_OPEN_DELAY, None)]
    for char in code:
        if mode == "unicode":
            events += [("unicode", char, False), ("unicode", char, True)]
        else:
            scan = SCAN_CODES.get(char.lower())
            if scan is None:
                raise ValueError(f"no scan code for {char!r}")
            events += [("scan", scan, False), ("scan", scan, True)]
    events += [("scan", SCAN_RETURN, False), ("scan", SCAN_RETURN, True)]
    return events


# US layout scan codes for letters and digits (set 1).
SCAN_CODES = {
    **dict(zip("1234567890", range(0x02, 0x0C))),
    **dict(zip("qwertyuiop", range(0x10, 0x1A))),
    **dict(zip("asdfghjkl", range(0x1E, 0x27))),
    **dict(zip("zxcvbnm", range(0x2C, 0x33))),
}


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    ULONG_PTR = wintypes.WPARAM

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class _INPUTUNION(ctypes.Union):
        # The mouse member is here only so the union has its real size; a
        # wrong-sized INPUT makes SendInput fail with ERROR_INVALID_PARAMETER.
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_SCANCODE = 0x0008
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SW_RESTORE = 9

    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    user32.IsWindowVisible.argtypes = (wintypes.HWND,)
    user32.IsIconic.argtypes = (wintypes.HWND,)
    user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    user32.GetAsyncKeyState.restype = ctypes.c_short
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = (WNDENUMPROC, wintypes.LPARAM)

    def _process_name(hwnd):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ""
        try:
            size = wintypes.DWORD(1024)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return ""
            return os.path.basename(buffer.value).lower()
        finally:
            kernel32.CloseHandle(handle)

    def find_game_window():
        """The visible StarCraft II game window, or None.

        Matched by the process behind the window (SC2_x64.exe), not the title:
        the Battle.net launcher and the editor are titled "StarCraft II" too.
        """
        found = []

        def callback(hwnd, _):
            if user32.IsWindowVisible(hwnd) and _process_name(hwnd) in GAME_EXES:
                found.append(hwnd)
                return False
            return True

        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return found[0] if found else None

    def game_is_foreground():
        hwnd = user32.GetForegroundWindow()
        return bool(hwnd) and _process_name(hwnd) in GAME_EXES

    def activate(hwnd):
        """Bring the game to the front. True once it is actually there."""
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        if not user32.SetForegroundWindow(hwnd):
            # Windows only lets the foreground process hand focus over. A lone
            # Alt tap counts as input and lifts that restriction.
            _send([_key_input(scan=0, vk=0x12, up=False), _key_input(scan=0, vk=0x12, up=True)])
            user32.SetForegroundWindow(hwnd)
        time.sleep(AFTER_ACTIVATE_DELAY)
        return game_is_foreground()

    user32.GetKeyboardLayout.argtypes = (wintypes.DWORD,)
    user32.GetKeyboardLayout.restype = wintypes.HKL

    def keyboard_is_english(hwnd=None):
        """Is the window's keyboard layout an English one? Physical key presses
        (scan-code mode) go through the IME, and under Zhuyin they compose
        bopomofo instead of typing letters. Measured: layout 0x0404 (zh-TW)
        swallowed every key. A Chinese IME switched to its own English mode
        still reports 0x0404, so False means "may not work", not "will not"."""
        hwnd = hwnd or user32.GetForegroundWindow()
        thread = user32.GetWindowThreadProcessId(hwnd, None)
        layout = user32.GetKeyboardLayout(thread) or 0
        return (int(layout) & 0x3FF) == 0x09  # primary language: LANG_ENGLISH

    def modifiers_down():
        return any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in MODIFIER_VKS)

    def wait_for_modifiers_released(timeout=3.0):
        """After a Ctrl+Alt+<n> hotkey the keys are usually still held; typing
        then would send Ctrl+Alt+Enter instead of Enter. True once released."""
        deadline = time.monotonic() + timeout
        while modifiers_down():
            if time.monotonic() > deadline:
                return False
            time.sleep(0.02)
        return True

    def _key_input(scan, vk=0, up=False, unicode=False):
        flags = (KEYEVENTF_UNICODE if unicode else (KEYEVENTF_SCANCODE if not vk else 0)) | (KEYEVENTF_KEYUP if up else 0)
        item = INPUT(type=INPUT_KEYBOARD)
        item.u.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
        return item

    def _send(items):
        array = (INPUT * len(items))(*items)
        sent = user32.SendInput(len(items), array, ctypes.sizeof(INPUT))
        if sent != len(items):
            raise OSError(ctypes.get_last_error(), "SendInput was blocked")

    def play(events, key_delay=0.015):
        """Send a sequence from build_sequence, one key at a time."""
        for kind, value, up in events:
            if kind == "pause":
                time.sleep(value)
                continue
            if kind == "unicode":
                _send([_key_input(scan=ord(value), up=up, unicode=True)])
            else:
                _send([_key_input(scan=value, up=up)])
            time.sleep(key_delay)
