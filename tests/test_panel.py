"""Unit tests: cheat data, hotkey rules, settings file, key sequences.

Run: python -m unittest discover -s tests
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cheats  # noqa: E402
import config  # noqa: E402
import hotkeys  # noqa: E402
import winput  # noqa: E402


class CheatData(unittest.TestCase):
    def test_all_23_codes_unique(self):
        codes = [cheat.code for cheat in cheats.CHEATS]
        self.assertEqual(len(codes), 23)
        self.assertEqual(len(set(code.lower() for code in codes)), 23)

    def test_every_code_is_plain_ascii_letters_and_digits(self):
        # Scan-code mode can only type these.
        for cheat in cheats.CHEATS:
            self.assertRegex(cheat.code, r"^[A-Za-z0-9]+$", cheat.code)

    def test_every_cheat_in_a_known_category_and_every_category_used(self):
        used = {cheat.category for cheat in cheats.CHEATS}
        self.assertEqual(used, set(cheats.CATEGORIES))

    def test_five_common_cheats_get_ctrl_alt_1_to_5(self):
        common = [cheat.code for cheat in cheats.CHEATS if cheat.common]
        self.assertEqual(
            [cheats.DEFAULT_HOTKEYS[code] for code in common],
            [f"Ctrl+Alt+{n}" for n in range(1, 6)],
        )

    def test_instant_defeat_asks_first_and_has_no_hotkey(self):
        defeat = cheats.by_code("LetsJustBugOutAndCallItEven")
        self.assertTrue(defeat.confirm)
        self.assertNotIn(defeat.code, cheats.DEFAULT_HOTKEYS)

    def test_only_the_song_keeps_achievements(self):
        keep = [cheat.code for cheat in cheats.CHEATS if cheat.keeps_achievements]
        self.assertEqual(keep, ["OverEngineeredCodPiece"])


class HotkeyRules(unittest.TestCase):
    def test_parse_and_format_round_trip(self):
        self.assertEqual(hotkeys.parse("Ctrl+Alt+1"), (hotkeys.MOD_CONTROL | hotkeys.MOD_ALT, 0x31))
        self.assertEqual(hotkeys.parse("ctrl + shift + f5"), (hotkeys.MOD_CONTROL | hotkeys.MOD_SHIFT, 0x74))
        self.assertEqual(hotkeys.format_hotkey(["Alt", "Ctrl"], "q"), "Ctrl+Alt+Q")
        self.assertEqual(hotkeys.format_from(hotkeys.parse("Shift+Alt+F12")), "Alt+Shift+F12")

    def test_bad_input_is_a_value_error(self):
        for text in ["", "Ctrl+", "Meta+1", "Ctrl+Alt+Enter"]:
            with self.assertRaises(ValueError, msg=text):
                hotkeys.parse(text)

    def test_single_modifier_or_bare_key_is_refused(self):
        # Ctrl+1 is a control group, Shift+1 adds to one, a bare key is typing.
        for text in ["1", "Ctrl+1", "Shift+1", "Alt+1", "F5"]:
            self.assertIsNotNone(hotkeys.problem(text), text)
        for text in ["Ctrl+Alt+1", "Ctrl+Shift+F5", "Alt+Shift+Q"]:
            self.assertIsNone(hotkeys.problem(text), text)

    def test_defaults_pass_the_rules_and_do_not_clash(self):
        for hotkey in cheats.DEFAULT_HOTKEYS.values():
            self.assertIsNone(hotkeys.problem(hotkey))
        self.assertEqual(hotkeys.conflicts(cheats.DEFAULT_HOTKEYS), {})

    def test_same_tolerates_garbage_from_a_hand_edited_file(self):
        self.assertTrue(hotkeys.same("Ctrl+Alt+1", "alt+ctrl+1"))
        self.assertFalse(hotkeys.same("Ctrl+Alt+1", "Ctrl+Alt+2"))
        self.assertFalse(hotkeys.same("banana", "Ctrl+Alt+1"))
        self.assertFalse(hotkeys.same("", ""))

    def test_conflicts_found_regardless_of_spelling(self):
        found = hotkeys.conflicts({"A": "Ctrl+Alt+1", "B": "alt+ctrl+1", "C": "", "D": "Ctrl+Alt+2"})
        self.assertEqual(found, {"Ctrl+Alt+1": ["A", "B"]})


class SettingsFile(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "settings.json")

    def test_missing_file_is_defaults(self):
        settings = config.load(self.path)
        self.assertTrue(settings["always_on_top"])
        self.assertEqual(settings["input_mode"], "unicode")
        self.assertEqual(settings["hotkeys"]["TerribleTerribleDamage"], "Ctrl+Alt+1")
        self.assertEqual(settings["hotkeys"]["SpectralTiger"], "")

    def test_save_then_load_round_trip(self):
        settings = config.defaults()
        settings["always_on_top"] = False
        settings["hotkeys"]["SpectralTiger"] = "Ctrl+Shift+F1"
        config.save(settings, self.path)
        self.assertEqual(config.load(self.path), settings)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_broken_file_is_kept_aside_and_defaults_used(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{ not json")
        self.assertEqual(config.load(self.path), config.defaults())
        self.assertTrue(os.path.exists(self.path + ".bad"))

    def test_unknown_codes_and_bad_values_are_ignored(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"input_mode": "telepathy", "key_delay_ms": 9999, "hotkeys": {"NotACheat": "Ctrl+Alt+9"}}, handle)
        settings = config.load(self.path)
        self.assertEqual(settings["input_mode"], "unicode")
        self.assertEqual(settings["key_delay_ms"], 15)
        self.assertNotIn("NotACheat", settings["hotkeys"])

    def test_panel_hotkey_and_strip_position(self):
        settings = config.load(self.path)
        self.assertEqual(settings["panel_hotkey"], "Ctrl+Alt+0")
        self.assertIsNone(settings["strip_position"])
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"panel_hotkey": "Ctrl+0", "strip_position": [100, "x"]}, handle)
        settings = config.load(self.path)
        self.assertEqual(settings["panel_hotkey"], "Ctrl+Alt+0", "one modifier is refused, like any hotkey")
        self.assertIsNone(settings["strip_position"])
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"panel_hotkey": "Ctrl+Shift+F9", "strip_position": [100, 40]}, handle)
        settings = config.load(self.path)
        self.assertEqual((settings["panel_hotkey"], settings["strip_position"]), ("Ctrl+Shift+F9", [100, 40]))

    def test_a_cheat_on_the_panel_hotkey_loses_it(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"hotkeys": {"SpectralTiger": "Alt+Ctrl+0"}}, handle)
        self.assertEqual(config.load(self.path)["hotkeys"]["SpectralTiger"], "")

    def test_achievement_mode_off_by_default_and_remembered(self):
        self.assertFalse(config.load(self.path)["achievement_mode"])
        settings = config.defaults()
        settings["achievement_mode"] = True
        config.save(settings, self.path)
        self.assertTrue(config.load(self.path)["achievement_mode"])
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"achievement_mode": "yes"}, handle)
        self.assertFalse(config.load(self.path)["achievement_mode"], "only a real true/false counts")

    def test_click_only_cheat_never_gets_a_hotkey_from_the_file(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"hotkeys": {"LetsJustBugOutAndCallItEven": "Ctrl+Alt+9"}}, handle)
        self.assertEqual(config.load(self.path)["hotkeys"]["LetsJustBugOutAndCallItEven"], "")


class KeySequence(unittest.TestCase):
    def test_unicode_mode_is_enter_code_enter(self):
        events = winput.build_sequence("HanShotFirst")
        self.assertEqual(events[:2], [("scan", 0x1C, False), ("scan", 0x1C, True)])
        self.assertEqual(events[2][0], "pause")
        typed = "".join(value for kind, value, up in events if kind == "unicode" and not up)
        self.assertEqual(typed, "HanShotFirst")
        self.assertEqual(events[-2:], [("scan", 0x1C, False), ("scan", 0x1C, True)])

    def test_every_key_down_has_its_key_up(self):
        events = [event for event in winput.build_sequence("Bunker55AliveInside", "scancode") if event[0] != "pause"]
        self.assertEqual(sum(1 for event in events if not event[2]), sum(1 for event in events if event[2]))

    def test_scancode_mode_can_type_every_cheat(self):
        for cheat in cheats.CHEATS:
            winput.build_sequence(cheat.code, "scancode")

    def test_scancode_mode_uses_the_letter_keys(self):
        events = winput.build_sequence("Aq1", "scancode")
        downs = [value for kind, value, up in events if kind == "scan" and not up]
        self.assertEqual(downs, [0x1C, 0x1E, 0x10, 0x02, 0x1C])

    def test_unknown_mode_refused(self):
        with self.assertRaises(ValueError):
            winput.build_sequence("x", "morse")


class MissionList(unittest.TestCase):
    def test_3_prologue_19_main_3_epilogue_all_distinct(self):
        import missions

        counts = [len(missions.in_part(part)) for part in missions.PARTS]
        self.assertEqual(counts, [3, 19, 3])
        self.assertEqual(len({mission.name for mission in missions.MISSIONS}), 25)

    def test_links_are_encoded(self):
        import missions

        rakshir = next(mission for mission in missions.MISSIONS if mission.name == "Rak'Shir")
        for url in (missions.video_url(rakshir), missions.wiki_url(rakshir), missions.chinese_url(rakshir)):
            self.assertTrue(url.startswith("https://"), url)
            self.assertNotIn(" ", url)
            self.assertNotIn("'", url)
        self.assertIn("brutal", missions.video_url(rakshir))
        self.assertIn("%E6%AE%98%E9%85%B7", missions.chinese_url(rakshir))  # 殘酷


class StripPlacement(unittest.TestCase):
    def test_strip_stays_on_screen(self):
        import app

        self.assertEqual(app.clamp_to_screen(100, 50, 190, 28, 1920, 1080), (100, 50))
        self.assertEqual(app.clamp_to_screen(3000, 2000, 190, 28, 1920, 1080), (1730, 1052))
        self.assertEqual(app.clamp_to_screen(-40, -5, 190, 28, 1920, 1080), (0, 0))


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class WindowsPlumbing(unittest.TestCase):
    def test_input_struct_has_the_size_sendinput_expects(self):
        import ctypes

        # 40 bytes on 64-bit Windows, 28 on 32-bit; anything else and every
        # SendInput call fails with ERROR_INVALID_PARAMETER.
        self.assertEqual(ctypes.sizeof(winput.INPUT), 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)

    def test_window_lookups_do_not_crash_without_the_game(self):
        winput.find_game_window()
        self.assertIsInstance(winput.game_is_foreground(), bool)


if __name__ == "__main__":
    unittest.main()
