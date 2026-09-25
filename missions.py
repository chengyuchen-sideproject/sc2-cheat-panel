"""Legacy of the Void missions, for the strategy lookup tab.

Names and order from the StarCraft Wiki mission tree ("Legacy of the Void
missions" navbox, read 2026-09-26): 3 prologue, 19 main, 3 epilogue. Where
the tree branches (e.g. Sky Shield / Amon's Reach) either order is allowed in
game; the list follows the tree top to bottom.

The Chinese labels are this project's own translations, not the in-game
Traditional Chinese names; the English name is what the searches use.
"""

from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class Mission:
    name: str  # official English name
    gloss: str  # Chinese translation (ours, not the game's)
    part: str


PARTS = ["序章：遺忘之語", "主線", "終章：進入虛空"]

MISSIONS = [
    Mission("Dark Whispers", "黑暗低語", PARTS[0]),
    Mission("Ghosts in the Fog", "迷霧中的幽靈", PARTS[0]),
    Mission("Evil Awoken", "邪惡甦醒", PARTS[0]),
    Mission("For Aiur!", "為了艾爾！", PARTS[1]),
    Mission("The Growing Shadow", "漸長的陰影", PARTS[1]),
    Mission("The Spear of Adun", "亞頓之矛", PARTS[1]),
    Mission("Sky Shield", "天空之盾", PARTS[1]),
    Mission("Amon's Reach", "亞蒙的觸手", PARTS[1]),
    Mission("Brothers in Arms", "並肩作戰", PARTS[1]),
    Mission("Last Stand", "最後防線", PARTS[1]),
    Mission("Forbidden Weapon", "禁忌武器", PARTS[1]),
    Mission("Temple of Unification", "統一神殿", PARTS[1]),
    Mission("The Infinite Cycle", "無盡輪迴", PARTS[1]),
    Mission("Harbinger of Oblivion", "毀滅先驅", PARTS[1]),
    Mission("Unsealing the Past", "解封過往", PARTS[1]),
    Mission("Steps of the Rite", "儀式之階", PARTS[1]),
    Mission("Purification", "淨化", PARTS[1]),
    Mission("Rak'Shir", "拉克希爾", PARTS[1]),
    Mission("Templar's Charge", "聖堂衝鋒", PARTS[1]),
    Mission("Templar's Return", "聖堂歸來", PARTS[1]),
    Mission("The Host", "宿主", PARTS[1]),
    Mission("Salvation", "救贖", PARTS[1]),
    Mission("Into the Void", "進入虛空", PARTS[2]),
    Mission("The Essence of Eternity", "永恆本質", PARTS[2]),
    Mission("Amon's Fall", "亞蒙的殞落", PARTS[2]),
]


def in_part(part):
    return [mission for mission in MISSIONS if mission.part == part]


def video_url(mission):
    """YouTube search for a Brutal run of this mission."""
    return "https://www.youtube.com/results?search_query=" + quote_plus(
        f"Legacy of the Void {mission.name} brutal guide"
    )


def wiki_url(mission):
    """Liquipedia's search, which jumps straight to the mission page when the
    name matches; a search rather than a guessed page title, which may change."""
    return "https://liquipedia.net/starcraft2/index.php?search=" + quote_plus(f"{mission.name} Legacy of the Void")


def chinese_url(mission):
    """Chinese-language write-ups (巴哈姆特 and others) via a web search."""
    return "https://www.google.com/search?q=" + quote_plus(f"虛空之遺 {mission.name} 殘酷 攻略")
