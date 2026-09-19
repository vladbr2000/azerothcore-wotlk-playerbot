from pathlib import Path

ROOT = Path("modules/mod-playerbots")

def replace_exact(path, old, new, expected=1):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s), found {count}: {old[:100]!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")
    print(f"patched {path}: {count} replacement(s)")

# Above level 80, WotLK has no additional talent templates. Reuse the level-80
# template instead of indexing premadeSpec arrays with the real level (>99).
replace_exact(
    "src/Bot/Factory/PlayerbotFactory.cpp",
    "    int startLevel = bot->GetLevel();",
    "    int startLevel = std::min<int>(bot->GetLevel(), 80);",
    expected=2,
)

# Avoid unsigned underflow in the replacement-age heuristic once bot level > 80.
replace_exact(
    "src/Bot/Factory/PlayerbotFactory.cpp",
    "    uint32 delta = 1 + (80 - bot->GetLevel()) / 10;",
    "    uint32 delta = bot->GetLevel() < 80 ? 1 + (80 - bot->GetLevel()) / 10 : 1;",
)

# Level 255 + 1 must not wrap to 0.
replace_exact(
    "src/Bot/RandomPlayerbotMgr.cpp",
    "    uint8 level = bot->GetLevel() + 1;",
    "    uint32 level = uint32(bot->GetLevel()) + 1;",
)

# PrintStats used uint8 iteration. At max level 255, ++i wrapped to 0 and could loop forever.
replace_exact(
    "src/Bot/RandomPlayerbotMgr.cpp",
    "    uint8 maxBotLevel = 0;",
    "    uint32 maxBotLevel = 0;",
)
replace_exact(
    "src/Bot/RandomPlayerbotMgr.cpp",
    "    for (uint8 i = 1; i <= maxBotLevel; ++i)",
    "    for (uint32 i = 1; i <= maxBotLevel; ++i)",
)

print("CoA level-255 Playerbots safety patch applied successfully.")
