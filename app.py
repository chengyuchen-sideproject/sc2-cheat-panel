"""StarCraft II cheat panel: click a cheat, or press its hotkey in game.

Run with Run.bat (pythonw, no console window) or `python app.py`.
"""

import queue
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import config
import hotkeys
import missions
import winput
from cheats import ACHIEVEMENT_WARNING, CATEGORIES, by_code, in_category

FONT = ("Microsoft JhengHei UI", 10)
FONT_SMALL = ("Microsoft JhengHei UI", 9)
FONT_BOLD = ("Microsoft JhengHei UI", 10, "bold")
MUTED = "#6B6B6B"
WARN_BG = "#FFF4E0"
SAFE_BG = "#E6F4EA"
SAFE_FG = "#1A7F37"
LINK = "#1E6FD9"

INPUT_MODES = {"unicode": "不經過輸入法（建議）", "scancode": "模擬實體按鍵（備用）"}

# The hotkey thread's name for the show/hide hotkey; never a cheat code.
PANEL_KEY = "__panel__"


class App:
    def __init__(self, root):
        self.root = root
        self.settings = config.load()
        self.events = queue.Queue()
        self.sending = threading.Lock()
        self.hotkey_labels = {}
        self.cheat_buttons = []

        root.title("星海2 密技面板")
        root.geometry("460x680")
        root.minsize(380, 420)
        root.attributes("-topmost", self.settings["always_on_top"])
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.game_status = tk.Label(root, font=FONT_BOLD, anchor="w", padx=10, pady=6)
        self.game_status.pack(fill="x")

        tabs = ttk.Notebook(root)
        tabs.pack(fill="both", expand=True)
        cheats_tab = tk.Frame(tabs)
        guide_tab = tk.Frame(tabs)
        tabs.add(cheats_tab, text="密技")
        tabs.add(guide_tab, text="虛空之遺攻略")

        # One banner, two faces: the warning while cheats are live, the
        # all-clear in achievement mode. No space after the sign: the wrap
        # would break there and leave it alone on a line.
        self.banner = tk.Label(cheats_tab, font=FONT_SMALL, anchor="w", justify="left", wraplength=430, padx=10, pady=6)
        self.banner.pack(fill="x")
        self._build_list(cheats_tab)
        self._build_guide(guide_tab)
        self._build_footer()
        self.strip = Strip(self)
        self._show_achievement_mode()

        self.hotkey_thread = hotkeys.HotkeyThread(
            on_press=lambda code: self.events.put(("hotkey", code)),
            on_failed=lambda failed: self.events.put(("failed", failed)),
        )
        self.hotkey_thread.start()
        self._register_hotkeys()

        self.set_status(f"點按鈕，或在遊戲裡按熱鍵。{self.settings['panel_hotkey']} 收起／叫出面板。")
        self._poll_events()
        self._poll_game()

    # --- expanded panel / folded strip ---------------------------------------

    def collapse(self):
        """Fold into the strip so nothing covers the game."""
        self.root.withdraw()
        self.strip.show()

    def expand(self):
        self.strip.hide()
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", self.settings["always_on_top"])

    def toggle(self):
        if self.root.state() == "withdrawn":
            self.expand()
        else:
            self.collapse()

    def _register_hotkeys(self):
        """In achievement mode only the panel's own hotkey stays registered: a
        cheat hotkey pressed by accident would cost the whole campaign save its
        achievements, so the keys are released, not merely ignored."""
        cheats_keys = {} if self.settings["achievement_mode"] else self.settings["hotkeys"]
        self.hotkey_thread.set_hotkeys({**cheats_keys, PANEL_KEY: self.settings["panel_hotkey"]})

    # --- achievement mode -----------------------------------------------------

    def set_achievement_mode(self, on):
        if not on and self.settings["achievement_mode"] and not messagebox.askyesno(
            "關掉成就模式？",
            "關掉之後熱鍵會重新生效，一按到就會送出密技，這份劇情存檔就拿不到成就了。\n\n確定要關掉嗎？",
        ):
            self.achievement.set(True)
            return
        self.settings["achievement_mode"] = on
        # The checkbox follows whatever route switched it, not only its own click.
        self.achievement.set(on)
        config.save(self.settings)
        self._register_hotkeys()
        self._show_achievement_mode()
        self.set_status("🏆 成就模式開著：密技按鈕和熱鍵都停用了。" if on else "成就模式已關閉，密技可以用了。")

    def _show_achievement_mode(self):
        on = self.settings["achievement_mode"]
        state = "disabled" if on else "normal"
        for button in self.cheat_buttons:
            button.configure(state=state)
        for label in self.hotkey_labels.values():
            label.configure(fg=MUTED if on else LINK, cursor="arrow" if on else "hand2")
        if on:
            self.banner.configure(
                text="🏆 成就模式：密技按鈕和熱鍵全部停用，不會誤觸。要用密技請先在下面關掉。", bg=SAFE_BG, fg=SAFE_FG,
            )
        else:
            self.banner.configure(text=f"⚠{ACHIEVEMENT_WARNING}", bg=WARN_BG, fg="black")
        self.strip.set_mode(on)

    # --- layout -------------------------------------------------------------

    def _scrollable(self, parent):
        """A vertically scrolling frame. The wheel scrolls whichever list the
        pointer is over — there are two, one per tab."""
        outer = tk.Frame(parent)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        scroll = lambda event: canvas.yview_scroll(int(-event.delta / 120), "units")  # noqa: E731
        outer.bind("<Enter>", lambda _: self.root.bind_all("<MouseWheel>", scroll))
        return inner

    def _build_list(self, parent):
        inner = self._scrollable(parent)
        for category in CATEGORIES:
            tk.Label(inner, text=category, font=FONT_BOLD, anchor="w", padx=10, pady=(4)).pack(fill="x", pady=(8, 0))
            for cheat in in_category(category):
                self._build_row(inner, cheat)

    def _build_row(self, parent, cheat):
        row = tk.Frame(parent, padx=10, pady=3)
        row.pack(fill="x")
        row.columnconfigure(1, weight=1)
        button = tk.Button(row, text=cheat.name, font=FONT, width=14, command=lambda: self.on_click(cheat))
        button.grid(row=0, column=0, rowspan=2, sticky="nw")
        self.cheat_buttons.append(button)
        tk.Label(row, text=cheat.effect, font=FONT_SMALL, anchor="w", justify="left", wraplength=230).grid(
            row=0, column=1, sticky="w", padx=8
        )
        tk.Label(row, text=f"{cheat.code}　{cheat.note}", font=FONT_SMALL, fg=MUTED, anchor="w", justify="left",
                 wraplength=230).grid(row=1, column=1, sticky="w", padx=8)
        if cheat.confirm:
            # Irreversible: only by click, after a question. A hotkey would have
            # to ask that question over the game, which it cannot.
            tk.Label(row, text="只能用點的", font=FONT_SMALL, fg=MUTED).grid(row=0, column=2, sticky="ne")
            return
        label = tk.Label(row, font=FONT_SMALL, fg=LINK, cursor="hand2")
        label.grid(row=0, column=2, sticky="ne")
        label.bind("<Button-1>", lambda _: self.edit_hotkey(cheat))
        self.hotkey_labels[cheat.code] = label
        self._show_hotkey(cheat.code)

    def _build_guide(self, parent):
        """Every Legacy of the Void mission, each with links to Brutal guides."""
        tk.Label(
            parent, font=FONT_SMALL, anchor="w", justify="left", wraplength=430, padx=10, pady=6, bg="#EEF3FB",
            text="點關卡的連結，會用瀏覽器搜尋那一關的殘酷打法。殘酷固定「較快」速度不能調慢；大波進攻前記得存檔。"
                 "\n中文是本工具的意譯，不是遊戲內官方譯名；搜尋用英文原名。",
        ).pack(fill="x")
        inner = self._scrollable(parent)
        for part in missions.PARTS:
            tk.Label(inner, text=part, font=FONT_BOLD, anchor="w", padx=10).pack(fill="x", pady=(8, 0))
            for number, mission in enumerate(missions.in_part(part), start=1):
                row = tk.Frame(inner, padx=10, pady=2)
                row.pack(fill="x")
                row.columnconfigure(0, weight=1)
                tk.Label(row, text=f"{number}. {mission.name}", font=FONT, anchor="w").grid(row=0, column=0, sticky="w")
                tk.Label(row, text=mission.gloss, font=FONT_SMALL, fg=MUTED, anchor="w").grid(row=1, column=0, sticky="w")
                for column, (text, url) in enumerate(
                    [("影片", missions.video_url(mission)), ("Liquipedia", missions.wiki_url(mission)),
                     ("中文攻略", missions.chinese_url(mission))],
                    start=1,
                ):
                    link = tk.Label(row, text=text, font=FONT_SMALL, fg=LINK, cursor="hand2", padx=4)
                    link.grid(row=0, column=column, rowspan=2)
                    link.bind("<Button-1>", lambda _, url=url: webbrowser.open(url))

    def _build_footer(self):
        safety = tk.Frame(self.root, padx=10, pady=(4))
        safety.pack(fill="x")
        self.achievement = tk.BooleanVar(value=self.settings["achievement_mode"])
        tk.Checkbutton(
            safety, text="🏆 成就模式（停用所有密技，避免誤觸）", font=FONT_BOLD, variable=self.achievement,
            command=lambda: self.set_achievement_mode(self.achievement.get()),
        ).pack(side="left")
        footer = tk.Frame(self.root, padx=10, pady=6)
        footer.pack(fill="x")
        self.topmost = tk.BooleanVar(value=self.settings["always_on_top"])
        tk.Checkbutton(footer, text="永遠在最上層", font=FONT_SMALL, variable=self.topmost,
                       command=self.toggle_topmost).pack(side="left")
        self.mode = tk.StringVar(value=INPUT_MODES[self.settings["input_mode"]])
        box = ttk.Combobox(footer, textvariable=self.mode, values=list(INPUT_MODES.values()), state="readonly",
                           width=18, font=FONT_SMALL)
        box.pack(side="right")
        box.bind("<<ComboboxSelected>>", lambda _: self.change_mode())
        tk.Label(footer, text="輸入方式", font=FONT_SMALL).pack(side="right", padx=4)
        self.status = tk.Label(self.root, font=FONT_SMALL, anchor="w", padx=10, pady=4, bg="#F2F2F2",
                               justify="left", wraplength=440)
        self.status.pack(fill="x")

    def _show_hotkey(self, code):
        label = self.hotkey_labels.get(code)
        if label is not None:
            label.configure(text=self.settings["hotkeys"].get(code) or "＋設定熱鍵")

    # --- actions ------------------------------------------------------------

    def on_click(self, cheat):
        if self.settings["achievement_mode"]:
            return
        if cheat.confirm and not messagebox.askyesno("確定嗎？", f"「{cheat.name}」：{cheat.effect}\n\n確定要送出嗎？"):
            return
        # Out of the way before the game comes back to the front.
        self.collapse()
        threading.Thread(target=self.send, args=(cheat, False), daemon=True).start()

    def send(self, cheat, from_hotkey):
        """Runs off the UI thread: activating the game and typing take a moment."""
        # The last line of defence: nothing is typed in achievement mode, by
        # whatever route a request got here.
        if self.settings["achievement_mode"]:
            self.events.put(("status", "🏆 成就模式開著，沒有送出密技。"))
            return
        if not self.sending.acquire(blocking=False):
            self.events.put(("status", "上一個密技還在輸入中，請稍等。"))
            return
        try:
            if from_hotkey:
                # A hotkey pressed in another program must not type into it.
                if not winput.game_is_foreground():
                    self.events.put(("status", f"星海2 不是目前的視窗，沒有送出「{cheat.name}」。"))
                    return
                if not winput.wait_for_modifiers_released():
                    self.events.put(("status", "Ctrl／Alt 一直沒放開，沒有送出。"))
                    return
            else:
                hwnd = winput.find_game_window()
                if not hwnd:
                    self.events.put(("status", "找不到星海2。先進入遊戲（劇情任務中）再按。"))
                    return
                if not winput.activate(hwnd):
                    self.events.put(("status", "切換不到星海2 的視窗。遊戲請改用「視窗化（全螢幕）」模式。"))
                    return
            events = winput.build_sequence(cheat.code, self.settings["input_mode"])
            winput.play(events, key_delay=self.settings["key_delay_ms"] / 1000)
            done = f"已送出：{cheat.name}（{cheat.code}）"
            if self.settings["input_mode"] == "scancode" and not winput.keyboard_is_english():
                done += "。目前是中文輸入法，「模擬實體按鍵」可能被輸入法吃掉；沒生效就先切成英文，或改回「不經過輸入法」。"
            self.events.put(("status", done))
        except OSError:
            self.events.put((
                "status",
                "Windows 擋下了輸入。星海2 如果是用「系統管理員身分」執行，這個工具也要用系統管理員身分開。",
            ))
        finally:
            self.sending.release()

    def edit_hotkey(self, cheat):
        if self.settings["achievement_mode"]:
            return
        HotkeyDialog(self, cheat)

    def apply_hotkey(self, code, hotkey):
        """Store one assignment (clearing whoever held it), save, re-register."""
        for other, current in self.settings["hotkeys"].items():
            if other != code and hotkeys.same(current, hotkey):
                self.settings["hotkeys"][other] = ""
                self._show_hotkey(other)
        self.settings["hotkeys"][code] = hotkey
        self._show_hotkey(code)
        config.save(self.settings)
        self._register_hotkeys()

    def toggle_topmost(self):
        self.settings["always_on_top"] = self.topmost.get()
        self.root.attributes("-topmost", self.settings["always_on_top"])
        config.save(self.settings)

    def change_mode(self):
        chosen = next(key for key, label in INPUT_MODES.items() if label == self.mode.get())
        self.settings["input_mode"] = chosen
        config.save(self.settings)
        self.set_status(f"輸入方式改成：{INPUT_MODES[chosen]}")

    def set_status(self, text):
        self.status.configure(text=text)

    def close(self):
        self.hotkey_thread.stop()
        self.root.destroy()

    # --- loops --------------------------------------------------------------

    def _poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self.set_status(value)
                elif kind == "hotkey" and value == PANEL_KEY:
                    self.toggle()
                elif kind == "hotkey":
                    cheat = by_code(value)
                    if cheat is not None and not cheat.confirm:
                        threading.Thread(target=self.send, args=(cheat, True), daemon=True).start()
                elif kind == "failed":
                    self.set_status(f"這些熱鍵被其他程式佔用，沒有生效：{'、'.join(value)}。點它們換一組。")
        except queue.Empty:
            pass
        self.root.after(50, self._poll_events)

    def _poll_game(self):
        if winput.find_game_window():
            self.game_status.configure(text="✅ 已偵測到星海2", fg="#1A7F37")
        else:
            self.game_status.configure(text="⚪ 還沒偵測到星海2（進入遊戲後就能用）", fg=MUTED)
        self.root.after(2000, self._poll_game)


class Strip:
    """The panel folded away: a small bar, always on top, that expands on a
    click. Frameless so it stays small; dragged to wherever it is out of the
    way, and remembered there. Right-click for the menu (expand, quit)."""

    DRAG_THRESHOLD = 4  # pixels; less than this is a click, not a drag

    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.85)
        label = tk.Label(self.window, font=FONT_SMALL, cursor="fleur", padx=10, pady=3)
        label.pack(fill="both", expand=True)
        self.label = label
        label.bind("<ButtonPress-1>", self._press)
        label.bind("<B1-Motion>", self._drag)
        label.bind("<ButtonRelease-1>", self._release)
        menu = tk.Menu(self.window, tearoff=False)
        menu.add_command(label="展開面板", command=app.expand)
        menu.add_command(label="結束", command=app.close)
        label.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))
        self._start = None
        self._moved = False

    def set_mode(self, achievement):
        """The strip says which mode is on, so a glance at the corner of the
        screen answers 「can I press anything by accident right now?」."""
        hotkey = self.app.settings["panel_hotkey"]
        if achievement:
            self.label.configure(text=f"🏆 成就模式　{hotkey}", bg=SAFE_FG, fg="white")
        else:
            self.label.configure(text=f"⚡ 星海2 密技　{hotkey}", bg="#20242C", fg="#F2F2F2")
        if self.window.state() == "normal":
            self.show()  # the text changed width

    def show(self):
        # Sized by its text, not a fixed width: at 150% display scaling the
        # font grows and a fixed box cut the hotkey off.
        self.window.update_idletasks()
        self.width = max(self.window.winfo_reqwidth(), 120)
        self.height = max(self.window.winfo_reqheight(), 24)
        x, y = self._position()
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.window.deiconify()
        self.window.lift()

    def hide(self):
        self.window.withdraw()

    def _position(self):
        """The saved spot, or top centre — kept on screen if the resolution
        shrank since it was saved."""
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        saved = self.app.settings.get("strip_position")
        x, y = saved if saved else ((screen_w - self.width) // 2, 0)
        return clamp_to_screen(x, y, self.width, self.height, screen_w, screen_h)

    def _press(self, event):
        self._start = (event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y())
        self._moved = False

    def _drag(self, event):
        if self._start is None:
            return
        start_x, start_y, window_x, window_y = self._start
        dx, dy = event.x_root - start_x, event.y_root - start_y
        if abs(dx) + abs(dy) >= self.DRAG_THRESHOLD:
            self._moved = True
        if self._moved:
            self.window.geometry(f"+{window_x + dx}+{window_y + dy}")

    def _release(self, _event):
        if self._moved:
            self.app.settings["strip_position"] = [self.window.winfo_x(), self.window.winfo_y()]
            config.save(self.app.settings)
        else:
            self.app.expand()
        self._start = None


def clamp_to_screen(x, y, width, height, screen_w, screen_h):
    return max(0, min(x, screen_w - width)), max(0, min(y, screen_h - height))


class HotkeyDialog:
    """Ctrl / Alt / Shift checkboxes and a key, for one cheat."""

    def __init__(self, app, cheat):
        self.app = app
        self.cheat = cheat
        current = app.settings["hotkeys"].get(cheat.code) or "Ctrl+Alt+1"
        try:
            flags, vk = hotkeys.parse(current)
        except ValueError:
            flags, vk = hotkeys.MOD_CONTROL | hotkeys.MOD_ALT, hotkeys.KEYS["1"]

        self.window = tk.Toplevel(app.root)
        self.window.title(f"熱鍵：{cheat.name}")
        self.window.transient(app.root)
        self.window.attributes("-topmost", True)
        self.window.resizable(False, False)
        body = tk.Frame(self.window, padx=14, pady=12)
        body.pack()

        tk.Label(body, text=f"「{cheat.name}」的熱鍵", font=FONT_BOLD).grid(row=0, column=0, columnspan=4, sticky="w")
        self.mods = {}
        for column, name in enumerate(hotkeys.MODIFIER_ORDER):
            var = tk.BooleanVar(value=bool(flags & hotkeys.MODIFIERS[name]))
            tk.Checkbutton(body, text=name, variable=var, font=FONT).grid(row=1, column=column, sticky="w")
            self.mods[name] = var
        self.key = tk.StringVar(value=next(name for name, code in hotkeys.KEYS.items() if code == vk))
        ttk.Combobox(body, textvariable=self.key, values=list(hotkeys.KEYS), state="readonly", width=5,
                     font=FONT).grid(row=1, column=3, padx=(8, 0))
        tk.Label(body, text="建議 Ctrl+Alt+數字；星海2 本身用 Ctrl+數字 編隊。", font=FONT_SMALL, fg=MUTED).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(6, 8)
        )
        buttons = tk.Frame(body)
        buttons.grid(row=3, column=0, columnspan=4, sticky="e")
        tk.Button(buttons, text="清除熱鍵", font=FONT_SMALL, command=self.clear).pack(side="left", padx=4)
        tk.Button(buttons, text="取消", font=FONT_SMALL, command=self.window.destroy).pack(side="left", padx=4)
        tk.Button(buttons, text="確定", font=FONT_SMALL, command=self.confirm).pack(side="left", padx=4)
        self.window.grab_set()

    def confirm(self):
        hotkey = hotkeys.format_hotkey([name for name, var in self.mods.items() if var.get()], self.key.get())
        issue = hotkeys.problem(hotkey)
        if not issue and hotkeys.same(hotkey, self.app.settings["panel_hotkey"]):
            issue = f"{hotkey} 是收起／叫出面板用的，換一組吧。"
        if issue:
            messagebox.showwarning("這組不行", issue, parent=self.window)
            return
        holder = next(
            (code for code, current in self.app.settings["hotkeys"].items()
             if code != self.cheat.code and hotkeys.same(current, hotkey)),
            None,
        )
        if holder and not messagebox.askyesno(
            "已經有人用了", f"{hotkey} 目前是「{by_code(holder).name}」的熱鍵，要改給「{self.cheat.name}」嗎？",
            parent=self.window,
        ):
            return
        self.app.apply_hotkey(self.cheat.code, hotkey)
        self.app.set_status(f"「{self.cheat.name}」的熱鍵改成 {hotkey}")
        self.window.destroy()

    def clear(self):
        self.app.apply_hotkey(self.cheat.code, "")
        self.app.set_status(f"「{self.cheat.name}」不再有熱鍵")
        self.window.destroy()


def main():
    if sys.platform != "win32":
        print("This tool only runs on Windows.")
        return 1
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on high-DPI screens
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
