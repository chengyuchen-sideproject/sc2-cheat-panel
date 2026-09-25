"""Hands-on check of the Windows side, without StarCraft II.

Opens a text box, types a cheat into it with each input mode and checks the
text arrived exactly; then registers a hotkey, presses it with synthetic
input and checks it fired. Needs an interactive desktop (it takes focus for a
few seconds), so it is not part of the unit tests.

Run: python scripts/selftest.py
"""

import os
import sys
import threading
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hotkeys  # noqa: E402
import winput  # noqa: E402

CODE = "TerribleTerribleDamage"
results = []


def check(ok, label, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}{'  ' + detail if detail else ''}")


def typing_round(root, entry, mode):
    entry.delete(0, "end")
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()
    entry.focus_force()
    root.update()
    time.sleep(0.3)
    winput.play(winput.build_sequence(CODE, mode))
    root.update()
    time.sleep(0.2)
    root.update()
    typed = entry.get()
    expected = CODE if mode == "unicode" else CODE.lower()
    if mode == "scancode" and typed != expected and not winput.keyboard_is_english():
        # Physical keys go through the IME; under Zhuyin they compose bopomofo.
        # That is the documented limit of this mode, not a failure of the code.
        print(f"SKIP  typing ({mode})  a Chinese IME is active; switch to English to test this mode")
        return
    check(typed == expected, f"typing ({mode})", repr(typed))


def hotkey_round():
    fired = threading.Event()
    thread = hotkeys.HotkeyThread(on_press=lambda code: fired.set(), on_failed=lambda failed: print("failed:", failed))
    thread.start()
    thread.set_hotkeys({"Test": "Ctrl+Alt+9"})
    time.sleep(0.3)
    # Ctrl down, Alt down, 9 down/up, Alt up, Ctrl up — by virtual key.
    ki = winput._key_input
    winput._send([ki(0, 0x11), ki(0, 0x12), ki(0, 0x39), ki(0, 0x39, up=True)])
    check(fired.wait(2), "hotkey Ctrl+Alt+9 fires")
    check(winput.modifiers_down(), "modifiers seen as still held right after the hotkey")
    winput._send([ki(0, 0x12, up=True), ki(0, 0x11, up=True)])
    check(winput.wait_for_modifiers_released(1), "released modifiers detected")
    thread.stop()


def pump(root, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        root.update()
        time.sleep(0.02)


def panel_round(root, entry):
    """The real panel: a hotkey pressed while another window has focus must
    type nothing there, and a click with no game running must say so."""
    import tempfile

    import app as panel
    import config
    from cheats import by_code

    if winput.find_game_window():
        print("SKIP  panel safety checks (StarCraft II is running)")
        return
    # A scratch settings file: this test flips switches and must not leave
    # them flipped in the player's own settings.json.
    config.DEFAULT_PATH = os.path.join(tempfile.mkdtemp(), "settings.json")
    window = tk.Toplevel(root)
    instance = panel.App(window)
    pump(root, 1.0)

    entry.delete(0, "end")
    root.lift()
    root.focus_force()
    entry.focus_force()
    pump(root, 0.4)
    ki = winput._key_input
    winput._send([ki(0, 0x11), ki(0, 0x12), ki(0, 0x31), ki(0, 0x31, up=True), ki(0, 0x12, up=True), ki(0, 0x11, up=True)])
    pump(root, 1.5)
    check(entry.get() == "", "hotkey outside the game types nothing", repr(entry.get()))
    check("不是目前的視窗" in instance.status.cget("text"), "panel says why", instance.status.cget("text"))

    instance.send(by_code("TookTheRedPill"), False)
    pump(root, 0.3)
    check("找不到星海2" in instance.status.cget("text"), "click with no game says so", instance.status.cget("text"))

    # Ctrl+Alt+0 folds the panel into the strip and back.
    press_panel = [ki(0, 0x11), ki(0, 0x12), ki(0, 0x30), ki(0, 0x30, up=True), ki(0, 0x12, up=True), ki(0, 0x11, up=True)]
    winput._send(press_panel)
    pump(root, 0.6)
    check(window.state() == "withdrawn" and instance.strip.window.state() == "normal", "Ctrl+Alt+0 folds into the strip")
    winput._send(press_panel)
    pump(root, 0.6)
    check(window.state() == "normal" and instance.strip.window.state() == "withdrawn", "Ctrl+Alt+0 again expands")

    # A click on a cheat folds the panel before typing.
    instance.on_click(by_code("TookTheRedPill"))
    pump(root, 0.6)
    check(window.state() == "withdrawn", "clicking a cheat folds the panel away")
    instance.expand()
    pump(root, 0.2)

    achievement_round(root, instance, panel, by_code, press_panel)
    instance.hotkey_thread.stop()
    window.destroy()


def ctrl_alt_1_is_free():
    """Can this process register Ctrl+Alt+1? False while the panel holds it."""
    import ctypes

    user32 = ctypes.windll.user32
    if user32.RegisterHotKey(None, 999, hotkeys.MOD_CONTROL | hotkeys.MOD_ALT, 0x31):
        user32.UnregisterHotKey(None, 999)
        return True
    return False


def achievement_round(root, instance, panel, by_code, press_panel):
    check(not ctrl_alt_1_is_free(), "cheats live: the panel holds Ctrl+Alt+1")

    instance.set_achievement_mode(True)
    pump(root, 0.5)
    check(ctrl_alt_1_is_free(), "achievement mode releases Ctrl+Alt+1 (not just ignores it)")
    check(all(button.cget("state") == "disabled" for button in instance.cheat_buttons), "every cheat button disabled")
    check(instance.achievement.get() is True, "the checkbox shows it is on")
    instance.send(by_code("TerribleTerribleDamage"), True)
    pump(root, 0.2)
    check("成就模式" in instance.status.cget("text"), "a send attempt is refused", instance.status.cget("text"))
    check("成就模式" in instance.strip.label.cget("text"), "the strip shows achievement mode")
    winput._send(press_panel)
    pump(root, 0.6)
    check(instance.root.state() == "withdrawn", "Ctrl+Alt+0 still works in achievement mode")
    instance.expand()

    panel.messagebox.askyesno = lambda *args, **kwargs: True  # the "turn it off?" question
    instance.set_achievement_mode(False)
    pump(root, 0.5)
    check(not ctrl_alt_1_is_free(), "turning it off takes Ctrl+Alt+1 back")


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # the Chinese status lines, readable when piped
    root = tk.Tk()
    root.title("selftest")
    entry = tk.Entry(root, width=40)
    entry.pack(padx=20, pady=20)
    root.update()
    for mode in ("unicode", "scancode"):
        typing_round(root, entry, mode)
    hotkey_round()
    panel_round(root, entry)
    hwnd = winput.find_game_window()
    check(hwnd is None or isinstance(hwnd, int), "game window lookup runs", "found" if hwnd else "game not running")
    root.destroy()
    print(f"\n{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
