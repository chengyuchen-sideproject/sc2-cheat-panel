"""StarCraft II single-player cheat codes and what they do.

Sources (cross-checked, all three agree on the 23 codes):
  - Blizzard News, "Game Guide: StarCraft II Cheat Codes"
  - Game Informer, "Full List Of StarCraft II Cheats" (2010-12-03)
  - Game Rant, "StarCraft 2: Every Cheat Code In The Game"

Cheats work in the single-player campaign only. Using any of them (except
OverEngineeredCodPiece) stops achievements for the rest of that campaign
save, until a new campaign is started or a save from before the first cheat
is loaded.

The descriptions shown to the player are Traditional Chinese on purpose; the
code itself stays in English.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Cheat:
    code: str
    name: str  # short label on the button
    effect: str  # one line shown under the button
    category: str
    note: str = ""  # where it works, caveats
    common: bool = False  # listed first; gets a default hotkey
    confirm: bool = False  # ask before sending (irreversible, e.g. instant defeat)
    keeps_achievements: bool = False


# Categories in the order they are shown.
CATEGORIES = ["常用", "資源", "戰鬥", "建造與科技", "任務", "劇情畫面", "彩蛋"]

MISSION_ONLY = "任務中輸入"
STORY_SCREEN = "在艦橋／劇情畫面輸入；主要適用《自由之翼》"

CHEATS = [
    # --- 常用: the five with default hotkeys ---------------------------------
    Cheat("TerribleTerribleDamage", "無敵", "我方單位不會受傷，攻擊力大增（再輸入一次關閉）", "常用", MISSION_ONLY, common=True),
    Cheat("WhoRunBartertown", "資源 +5000", "晶礦和瓦斯各加 5000", "常用", MISSION_ONLY, common=True),
    Cheat("CatFoodForPrawnGuns", "快速建造", "建造、訓練、升級都變很快", "常用", MISSION_ONLY, common=True),
    Cheat("Bunker55AliveInside", "無人口上限", "不需要補給站／王蟲／水晶塔", "常用", MISSION_ONLY, common=True),
    Cheat("TookTheRedPill", "全開地圖", "關閉戰爭迷霧，整張地圖都看得到", "常用", MISSION_ONLY, common=True),
    # --- 資源 -------------------------------------------------------------------
    Cheat("SpectralTiger", "晶礦 +5000", "只加晶礦 5000", "資源", MISSION_ONLY),
    Cheat("RealMenDrillDeep", "瓦斯 +5000", "只加瓦斯 5000", "資源", MISSION_ONLY),
    Cheat("MoreDotsMoreDots", "全部免費", "所有單位和建築都不花資源", "資源", MISSION_ONLY),
    # --- 戰鬥 -------------------------------------------------------------------
    Cheat("HanShotFirst", "技能無冷卻", "技能施放後不用等冷卻", "戰鬥", MISSION_ONLY),
    Cheat("ImADoctorNotARoachJim", "快速回血", "單位回血速度大幅加快", "戰鬥", MISSION_ONLY),
    # --- 建造與科技 --------------------------------------------------------------
    Cheat("SoSayWeAll", "全科技", "不用前置建築，所有科技都能用", "建造與科技", MISSION_ONLY),
    Cheat("IAmIronMan", "全升級", "所有升級立即完成、免費", "建造與科技", MISSION_ONLY),
    # --- 任務 -------------------------------------------------------------------
    Cheat("WhatIsBestInLife", "直接過關", "立即獲勝", "任務", MISSION_ONLY),
    Cheat("NeverGiveUpNeverSurrender", "輸了也能繼續", "被打敗後仍可繼續玩", "任務", MISSION_ONLY),
    Cheat("TyuHasLeftTheGame", "達成也不結束", "關閉勝利條件，可以繼續玩下去", "任務", MISSION_ONLY),
    Cheat("LetsJustBugOutAndCallItEven", "直接失敗", "立即判定失敗（會先問你確定嗎）", "任務", MISSION_ONLY, confirm=True),
    # --- 劇情畫面 ---------------------------------------------------------------
    Cheat("WhySoSerious", "點數 +500 萬", "劇情點數加 500 萬，軍械庫、酒吧全買得起", "劇情畫面", STORY_SCREEN + "；《蟲族之心》無效"),
    Cheat("LeaveYourSleep", "開啟所有任務", "所有任務都能直接選", "劇情畫面", STORY_SCREEN),
    Cheat("HoradricCube", "開啟所有研究", "所有研究選項都開放", "劇情畫面", STORY_SCREEN),
    Cheat("EyeOfSauron", "開啟所有過場動畫", "所有過場動畫都能看", "劇情畫面", STORY_SCREEN),
    Cheat("StayClassyMarSara", "開啟所有新聞", "所有 UNN 電視新聞都能看", "劇情畫面", STORY_SCREEN + "；《蟲族之心》無效"),
    # --- 彩蛋 -------------------------------------------------------------------
    Cheat("OverEngineeredCodPiece", "播放歌曲", "播放〈Terran Up the Night〉，不影響成就", "彩蛋", MISSION_ONLY, keeps_achievements=True),
    Cheat("Jaynestown", "地嶽晶 +5000", "加 5000 地嶽晶（Terrazine）", "彩蛋", "只在自訂地圖有效"),
]

# Default hotkeys for the common five: Ctrl+Alt+<n>. StarCraft II uses Ctrl+<n>
# for control groups and most F-keys, and binds nothing to Ctrl+Alt.
DEFAULT_HOTKEYS = {
    cheat.code: f"Ctrl+Alt+{index}" for index, cheat in enumerate([c for c in CHEATS if c.common], start=1)
}

ACHIEVEMENT_WARNING = (
    "用了密技（播歌的彩蛋除外），這個劇情存檔之後就拿不到成就；"
    "要開新劇情或讀取第一次用密技之前的存檔才會恢復。"
)


def by_code(code):
    for cheat in CHEATS:
        if cheat.code == code:
            return cheat
    return None


def in_category(category):
    return [cheat for cheat in CHEATS if cheat.category == category]
