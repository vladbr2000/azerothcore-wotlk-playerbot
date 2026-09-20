from pathlib import Path

ROOT = Path("source")
BOT = ROOT / "modules" / "mod-playerbots"

def replace_exact(path: Path, old: str, new: str, expected: int = 1):
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s), found {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"patched {path}: {count} replacement(s)")

# Core configuration: accept the engine's existing uint8 strong maximum (255).
world_config = ROOT / "src/server/game/World/WorldConfig.cpp"
replace_exact(
    world_config,
    'SetConfigValue<uint32>(CONFIG_MIN_LEVEL_STAT_SAVE, "PlayerSave.Stats.MinLevel", 0, ConfigValueCache::Reloadable::Yes, [](uint32 const& value) { return value < MAX_LEVEL; }, "< MAX_LEVEL");',
    'SetConfigValue<uint32>(CONFIG_MIN_LEVEL_STAT_SAVE, "PlayerSave.Stats.MinLevel", 0, ConfigValueCache::Reloadable::Yes, [](uint32 const& value) { return value < STRONG_MAX_LEVEL; }, "< STRONG_MAX_LEVEL");'
)
replace_exact(
    world_config,
    'SetConfigValue<uint32>(CONFIG_MAX_PLAYER_LEVEL, "MaxPlayerLevel", DEFAULT_MAX_LEVEL, ConfigValueCache::Reloadable::No, [](uint32 const& value) { return value > 0 && value <= MAX_LEVEL; }, "> 0 && <= MAX_LEVEL");',
    'SetConfigValue<uint32>(CONFIG_MAX_PLAYER_LEVEL, "MaxPlayerLevel", DEFAULT_MAX_LEVEL, ConfigValueCache::Reloadable::No, [](uint32 const& value) { return value > 0 && value <= STRONG_MAX_LEVEL; }, "> 0 && <= STRONG_MAX_LEVEL");'
)
replace_exact(
    world_config,
    'SetConfigValue<uint32>(CONFIG_START_GM_LEVEL, "GM.StartLevel", 1, ConfigValueCache::Reloadable::Yes, [](uint32 const& value) { return value <= MAX_LEVEL; }, "<= MAX_LEVEL");',
    'SetConfigValue<uint32>(CONFIG_START_GM_LEVEL, "GM.StartLevel", 1, ConfigValueCache::Reloadable::Yes, [](uint32 const& value) { return value <= STRONG_MAX_LEVEL; }, "<= STRONG_MAX_LEVEL");'
)
replace_exact(
    world_config,
    '// note: disable value (-1) will assigned as 0xFFFFFFF, to prevent overflow at calculations limit it to max possible player level MAX_LEVEL(100)\n'
    '    SetConfigValue<uint32>(CONFIG_QUEST_LOW_LEVEL_HIDE_DIFF, "Quests.LowLevelHideDiff", 4, ConfigValueCache::Reloadable::Yes, [](uint32 const& value) { return value <= MAX_LEVEL; }, "<= MAX_LEVEL");\n'
    '    SetConfigValue<uint32>(CONFIG_QUEST_HIGH_LEVEL_HIDE_DIFF, "Quests.HighLevelHideDiff", 7, ConfigValueCache::Reloadable::Yes, [](uint32 const& value) { return value <= MAX_LEVEL; }, "<= MAX_LEVEL");',
    '// note: disable value (-1) is assigned as an unsigned sentinel; keep configured differences within the strong player-level limit.\n'
    '    SetConfigValue<uint32>(CONFIG_QUEST_LOW_LEVEL_HIDE_DIFF, "Quests.LowLevelHideDiff", 4, ConfigValueCache::Reloadable::Yes, [](uint32 const& value) { return value <= STRONG_MAX_LEVEL; }, "<= STRONG_MAX_LEVEL");\n'
    '    SetConfigValue<uint32>(CONFIG_QUEST_HIGH_LEVEL_HIDE_DIFF, "Quests.HighLevelHideDiff", 7, ConfigValueCache::Reloadable::Yes, [](uint32 const& value) { return value <= STRONG_MAX_LEVEL; }, "<= STRONG_MAX_LEVEL");'
)

# GM absolute-level command: remove the stock level-80 clamp.
char_cmd = ROOT / "src/server/scripts/Commands/cs_character.cpp"
replace_exact(
    char_cmd,
    '        if (newlevel > DEFAULT_MAX_LEVEL)                         // hardcoded maximum level\n'
    '            newlevel = DEFAULT_MAX_LEVEL;',
    '        if (newlevel > STRONG_MAX_LEVEL)                          // server-side hard maximum level\n'
    '            newlevel = STRONG_MAX_LEVEL;'
)

# Existing CoA crash seen in the shipped bot binary: DynamicObject auras are not Unit-owned auras.
necro = ROOT / "modules/mod-ascension-compat/src/AscensionNecromancerAbilities.cpp"
replace_exact(
    necro,
    '        if (aura->GetUnitOwner() && aura->GetUnitOwner()->IsPlayer())\n'
    '        {\n'
    '            if (id == 504845)\n'
    '                duration = std::min(duration, 8000);\n'
    '            if (id == 803741 || id == 800706)\n'
    '                duration = std::min(duration, player->HasAura(302923) ? 9000 : 8000);\n'
    '        }',
    '        if (aura->GetType() == UNIT_AURA_TYPE)\n'
    '        {\n'
    '            Unit* owner = aura->GetUnitOwner();\n'
    '            if (owner && owner->IsPlayer())\n'
    '            {\n'
    '                if (id == 504845)\n'
    '                    duration = std::min(duration, 8000);\n'
    '                if (id == 803741 || id == 800706)\n'
    '                    duration = std::min(duration, player->HasAura(302923) ? 9000 : 8000);\n'
    '            }\n'
    '        }'
)

# At MaxPlayerLevel=255, max level + world-boss offset can overflow a uint8 and cap summons at a tiny level.
spell_effects = ROOT / "src/server/game/Spells/SpellEffects.cpp"
replace_exact(
    spell_effects,
    '    summonLevel = std::min<uint8>(sWorld->getIntConfig(CONFIG_MAX_PLAYER_LEVEL) + sWorld->getIntConfig(CONFIG_WORLD_BOSS_LEVEL_DIFF), std::max<uint8>(1U, summonLevel));',
    '    uint32 const summonLevelCap = std::min<uint32>(STRONG_MAX_LEVEL,\n'
    '        sWorld->getIntConfig(CONFIG_MAX_PLAYER_LEVEL) + sWorld->getIntConfig(CONFIG_WORLD_BOSS_LEVEL_DIFF));\n'
    '    summonLevel = std::min<uint8>(static_cast<uint8>(summonLevelCap), std::max<uint8>(1U, summonLevel));'
)

# Playerbots: WotLK premade-spec arrays only contain stock-era level templates.
# Above 80, reuse the level-80 template, then let the existing bot logic spend any remaining points.
factory = BOT / "src/Bot/Factory/PlayerbotFactory.cpp"
replace_exact(
    factory,
    '    int startLevel = bot->GetLevel();',
    '    int startLevel = std::min<int>(bot->GetLevel(), 80);',
    expected=2
)

# Avoid unsigned underflow once bot level is above 80.
replace_exact(
    factory,
    '    uint32 delta = 1 + (80 - bot->GetLevel()) / 10;',
    '    uint32 delta = bot->GetLevel() < 80 ? 1 + (80 - bot->GetLevel()) / 10 : 1;'
)

mgr = BOT / "src/Bot/RandomPlayerbotMgr.cpp"

# 255 + 1 must not wrap to zero before the max-level check.
replace_exact(
    mgr,
    '    uint8 level = bot->GetLevel() + 1;',
    '    uint32 level = uint32(bot->GetLevel()) + 1;'
)

# Stats reporting must not wrap its counter after level 255.
replace_exact(
    mgr,
    '    uint8 maxBotLevel = 0;',
    '    uint32 maxBotLevel = 0;'
)
replace_exact(
    mgr,
    '        maxBotLevel = std::max(maxBotLevel, bot->GetLevel());',
    '        maxBotLevel = std::max(maxBotLevel, static_cast<uint32>(bot->GetLevel()));'
)
replace_exact(
    mgr,
    '    for (uint8 i = 1; i <= maxBotLevel; ++i)',
    '    for (uint32 i = 1; i <= maxBotLevel; ++i)'
)

print("Exact CoA v1 playerbots level-255 compatibility patch applied.")
