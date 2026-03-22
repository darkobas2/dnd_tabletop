"""
character.py — D&D 5e character sheet reference data and helpers.

Contains class definitions, spell slot tables, proficiency bonus,
ability scores, skills, and everything needed for a full character sheet.
"""

from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Ability Scores
# ---------------------------------------------------------------------------

ABILITIES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

ABILITY_NAMES = {
    "STR": "Strength",
    "DEX": "Dexterity",
    "CON": "Constitution",
    "INT": "Intelligence",
    "WIS": "Wisdom",
    "CHA": "Charisma",
}

def ability_modifier(score: int) -> int:
    """Calculate ability modifier from score: (score - 10) // 2"""
    return (score - 10) // 2


# ---------------------------------------------------------------------------
# Skills (skill name -> governing ability)
# ---------------------------------------------------------------------------

SKILLS = {
    "Acrobatics": "DEX",
    "Animal Handling": "WIS",
    "Arcana": "INT",
    "Athletics": "STR",
    "Deception": "CHA",
    "History": "INT",
    "Insight": "WIS",
    "Intimidation": "CHA",
    "Investigation": "INT",
    "Medicine": "WIS",
    "Nature": "INT",
    "Perception": "WIS",
    "Performance": "CHA",
    "Persuasion": "CHA",
    "Religion": "INT",
    "Sleight of Hand": "DEX",
    "Stealth": "DEX",
    "Survival": "WIS",
}

# ---------------------------------------------------------------------------
# Proficiency Bonus by Level
# ---------------------------------------------------------------------------

def proficiency_bonus(level: int) -> int:
    """Return proficiency bonus for a given character level (1-20)."""
    if level < 1:
        return 2
    return (level - 1) // 4 + 2  # +2 at 1, +3 at 5, +4 at 9, +5 at 13, +6 at 17

# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

CLASSES = {
    "Barbarian": {
        "hit_die": 12,
        "save_proficiencies": ["STR", "CON"],
        "spellcaster": None,
        "armor_proficiencies": "Light, Medium, Shields",
        "weapon_proficiencies": "Simple, Martial",
    },
    "Bard": {
        "hit_die": 8,
        "save_proficiencies": ["DEX", "CHA"],
        "spellcaster": "full",
        "casting_ability": "CHA",
        "armor_proficiencies": "Light",
        "weapon_proficiencies": "Simple, Hand Crossbows, Longswords, Rapiers, Shortswords",
    },
    "Cleric": {
        "hit_die": 8,
        "save_proficiencies": ["WIS", "CHA"],
        "spellcaster": "full",
        "casting_ability": "WIS",
        "armor_proficiencies": "Light, Medium, Shields",
        "weapon_proficiencies": "Simple",
    },
    "Druid": {
        "hit_die": 8,
        "save_proficiencies": ["INT", "WIS"],
        "spellcaster": "full",
        "casting_ability": "WIS",
        "armor_proficiencies": "Light, Medium, Shields (nonmetal)",
        "weapon_proficiencies": "Clubs, Daggers, Darts, Javelins, Maces, Quarterstaffs, Scimitars, Sickles, Slings, Spears",
    },
    "Fighter": {
        "hit_die": 10,
        "save_proficiencies": ["STR", "CON"],
        "spellcaster": None,  # Eldritch Knight = "third" but we keep it simple
        "armor_proficiencies": "All armor, Shields",
        "weapon_proficiencies": "Simple, Martial",
    },
    "Monk": {
        "hit_die": 8,
        "save_proficiencies": ["STR", "DEX"],
        "spellcaster": None,
        "armor_proficiencies": "None",
        "weapon_proficiencies": "Simple, Shortswords",
    },
    "Paladin": {
        "hit_die": 10,
        "save_proficiencies": ["WIS", "CHA"],
        "spellcaster": "half",
        "casting_ability": "CHA",
        "armor_proficiencies": "All armor, Shields",
        "weapon_proficiencies": "Simple, Martial",
    },
    "Ranger": {
        "hit_die": 10,
        "save_proficiencies": ["STR", "DEX"],
        "spellcaster": "half",
        "casting_ability": "WIS",
        "armor_proficiencies": "Light, Medium, Shields",
        "weapon_proficiencies": "Simple, Martial",
    },
    "Rogue": {
        "hit_die": 8,
        "save_proficiencies": ["DEX", "INT"],
        "spellcaster": None,  # Arcane Trickster = "third"
        "armor_proficiencies": "Light",
        "weapon_proficiencies": "Simple, Hand Crossbows, Longswords, Rapiers, Shortswords",
    },
    "Sorcerer": {
        "hit_die": 6,
        "save_proficiencies": ["CON", "CHA"],
        "spellcaster": "full",
        "casting_ability": "CHA",
        "armor_proficiencies": "None",
        "weapon_proficiencies": "Daggers, Darts, Slings, Quarterstaffs, Light Crossbows",
    },
    "Warlock": {
        "hit_die": 8,
        "save_proficiencies": ["WIS", "CHA"],
        "spellcaster": "pact",
        "casting_ability": "CHA",
        "armor_proficiencies": "Light",
        "weapon_proficiencies": "Simple",
    },
    "Wizard": {
        "hit_die": 6,
        "save_proficiencies": ["INT", "WIS"],
        "spellcaster": "full",
        "casting_ability": "INT",
        "armor_proficiencies": "None",
        "weapon_proficiencies": "Daggers, Darts, Slings, Quarterstaffs, Light Crossbows",
    },
}

# ---------------------------------------------------------------------------
# Spell Slots Tables
# ---------------------------------------------------------------------------

# Full caster (Wizard, Sorcerer, Bard, Cleric, Druid)
# Key: level -> [1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, 9th]
FULL_CASTER_SLOTS = {
    1:  [2,0,0,0,0,0,0,0,0],
    2:  [3,0,0,0,0,0,0,0,0],
    3:  [4,2,0,0,0,0,0,0,0],
    4:  [4,3,0,0,0,0,0,0,0],
    5:  [4,3,2,0,0,0,0,0,0],
    6:  [4,3,3,0,0,0,0,0,0],
    7:  [4,3,3,1,0,0,0,0,0],
    8:  [4,3,3,2,0,0,0,0,0],
    9:  [4,3,3,3,1,0,0,0,0],
    10: [4,3,3,3,2,0,0,0,0],
    11: [4,3,3,3,2,1,0,0,0],
    12: [4,3,3,3,2,1,0,0,0],
    13: [4,3,3,3,2,1,1,0,0],
    14: [4,3,3,3,2,1,1,0,0],
    15: [4,3,3,3,2,1,1,1,0],
    16: [4,3,3,3,2,1,1,1,0],
    17: [4,3,3,3,2,1,1,1,1],
    18: [4,3,3,3,3,1,1,1,1],
    19: [4,3,3,3,3,2,1,1,1],
    20: [4,3,3,3,3,2,2,1,1],
}

# Half caster (Paladin, Ranger) — use caster level = class level // 2
HALF_CASTER_SLOTS = {
    1:  [0,0,0,0,0,0,0,0,0],
    2:  [2,0,0,0,0,0,0,0,0],
    3:  [3,0,0,0,0,0,0,0,0],
    4:  [3,0,0,0,0,0,0,0,0],
    5:  [4,2,0,0,0,0,0,0,0],
    6:  [4,2,0,0,0,0,0,0,0],
    7:  [4,3,0,0,0,0,0,0,0],
    8:  [4,3,0,0,0,0,0,0,0],
    9:  [4,3,2,0,0,0,0,0,0],
    10: [4,3,2,0,0,0,0,0,0],
    11: [4,3,3,0,0,0,0,0,0],
    12: [4,3,3,0,0,0,0,0,0],
    13: [4,3,3,1,0,0,0,0,0],
    14: [4,3,3,1,0,0,0,0,0],
    15: [4,3,3,2,0,0,0,0,0],
    16: [4,3,3,2,0,0,0,0,0],
    17: [4,3,3,3,1,0,0,0,0],
    18: [4,3,3,3,1,0,0,0,0],
    19: [4,3,3,3,2,0,0,0,0],
    20: [4,3,3,3,2,0,0,0,0],
}

# Warlock pact slots: level -> (num_slots, slot_level)
PACT_MAGIC_SLOTS = {
    1:  (1, 1), 2:  (2, 1), 3:  (2, 2), 4:  (2, 2),
    5:  (2, 3), 6:  (2, 3), 7:  (2, 4), 8:  (2, 4),
    9:  (2, 5), 10: (2, 5), 11: (3, 5), 12: (3, 5),
    13: (3, 5), 14: (3, 5), 15: (3, 5), 16: (3, 5),
    17: (4, 5), 18: (4, 5), 19: (4, 5), 20: (4, 5),
}

def get_spell_slots(character_class: str, level: int) -> List[int]:
    """Return list of [1st, 2nd, ..., 9th] spell slot counts for class+level."""
    if level < 1 or level > 20:
        return [0] * 9
    cls = CLASSES.get(character_class)
    if not cls:
        return [0] * 9

    caster_type = cls.get("spellcaster")
    if caster_type == "full":
        return list(FULL_CASTER_SLOTS.get(level, [0]*9))
    elif caster_type == "half":
        return list(HALF_CASTER_SLOTS.get(level, [0]*9))
    elif caster_type == "pact":
        num, slot_lvl = PACT_MAGIC_SLOTS.get(level, (0, 0))
        slots = [0] * 9
        if slot_lvl > 0 and num > 0:
            slots[slot_lvl - 1] = num
        return slots
    return [0] * 9


def get_hit_die(character_class: str) -> int:
    """Return hit die size for a class (e.g., 12 for Barbarian)."""
    cls = CLASSES.get(character_class)
    return cls["hit_die"] if cls else 8


def get_save_proficiencies(character_class: str) -> List[str]:
    """Return list of saving throw proficiency abilities for a class."""
    cls = CLASSES.get(character_class)
    return list(cls["save_proficiencies"]) if cls else []


def get_casting_ability(character_class: str) -> Optional[str]:
    """Return spellcasting ability for a class, or None if not a caster."""
    cls = CLASSES.get(character_class)
    if cls:
        return cls.get("casting_ability")
    return None


# ---------------------------------------------------------------------------
# Races (simplified — just common races with ability bonuses)
# ---------------------------------------------------------------------------

RACES = {
    "Human": {"bonus": {}, "speed": 30, "size": "Medium"},
    "Elf (High)": {"bonus": {"DEX": 2, "INT": 1}, "speed": 30, "size": "Medium"},
    "Elf (Wood)": {"bonus": {"DEX": 2, "WIS": 1}, "speed": 35, "size": "Medium"},
    "Elf (Dark/Drow)": {"bonus": {"DEX": 2, "CHA": 1}, "speed": 30, "size": "Medium"},
    "Dwarf (Hill)": {"bonus": {"CON": 2, "WIS": 1}, "speed": 25, "size": "Medium"},
    "Dwarf (Mountain)": {"bonus": {"CON": 2, "STR": 2}, "speed": 25, "size": "Medium"},
    "Halfling (Lightfoot)": {"bonus": {"DEX": 2, "CHA": 1}, "speed": 25, "size": "Small"},
    "Halfling (Stout)": {"bonus": {"DEX": 2, "CON": 1}, "speed": 25, "size": "Small"},
    "Half-Elf": {"bonus": {"CHA": 2}, "speed": 30, "size": "Medium"},
    "Half-Orc": {"bonus": {"STR": 2, "CON": 1}, "speed": 30, "size": "Medium"},
    "Gnome (Forest)": {"bonus": {"INT": 2, "DEX": 1}, "speed": 25, "size": "Small"},
    "Gnome (Rock)": {"bonus": {"INT": 2, "CON": 1}, "speed": 25, "size": "Small"},
    "Tiefling": {"bonus": {"CHA": 2, "INT": 1}, "speed": 30, "size": "Medium"},
    "Dragonborn": {"bonus": {"STR": 2, "CHA": 1}, "speed": 30, "size": "Medium"},
    "Goliath": {"bonus": {"STR": 2, "CON": 1}, "speed": 30, "size": "Medium"},
    "Aasimar": {"bonus": {"CHA": 2}, "speed": 30, "size": "Medium"},
    "Tabaxi": {"bonus": {"DEX": 2, "CHA": 1}, "speed": 30, "size": "Medium"},
    "Kenku": {"bonus": {"DEX": 2, "WIS": 1}, "speed": 30, "size": "Medium"},
    "Firbolg": {"bonus": {"WIS": 2, "STR": 1}, "speed": 30, "size": "Medium"},
    "Tortle": {"bonus": {"STR": 2, "WIS": 1}, "speed": 30, "size": "Medium"},
    "Custom": {"bonus": {}, "speed": 30, "size": "Medium"},
}


# ---------------------------------------------------------------------------
# CharacterSheet dataclass-like dict helpers
# ---------------------------------------------------------------------------

def new_character_sheet() -> dict:
    """Return a fresh empty character sheet dict."""
    return {
        "race": "Human",
        "character_class": "Fighter",
        "level": 1,
        "ability_scores": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
        "skill_proficiencies": [],
        "save_proficiencies": [],  # overridden by class, but can be customized
        "spell_slots_used": [0, 0, 0, 0, 0, 0, 0, 0, 0],
        "hit_dice_used": 0,
        "features": "",
        "equipment": "",
        "backstory": "",
    }


def calc_skill_bonus(sheet: dict, skill_name: str) -> int:
    """Calculate total skill bonus: ability_mod + proficiency (if proficient)."""
    ability = SKILLS.get(skill_name, "STR")
    score = sheet.get("ability_scores", {}).get(ability, 10)
    mod = ability_modifier(score)
    level = sheet.get("level", 1)
    if skill_name in sheet.get("skill_proficiencies", []):
        mod += proficiency_bonus(level)
    return mod


def calc_save_bonus(sheet: dict, ability: str) -> int:
    """Calculate saving throw bonus: ability_mod + proficiency (if proficient)."""
    score = sheet.get("ability_scores", {}).get(ability, 10)
    mod = ability_modifier(score)
    level = sheet.get("level", 1)
    saves = sheet.get("save_proficiencies", [])
    if not saves:
        # Default from class
        saves = get_save_proficiencies(sheet.get("character_class", ""))
    if ability in saves:
        mod += proficiency_bonus(level)
    return mod


def calc_spell_save_dc(sheet: dict) -> int:
    """Calculate spell save DC: 8 + proficiency + casting ability mod."""
    cls = sheet.get("character_class", "")
    casting_ab = get_casting_ability(cls)
    if not casting_ab:
        return 0
    score = sheet.get("ability_scores", {}).get(casting_ab, 10)
    return 8 + proficiency_bonus(sheet.get("level", 1)) + ability_modifier(score)


def calc_spell_attack(sheet: dict) -> int:
    """Calculate spell attack modifier: proficiency + casting ability mod."""
    cls = sheet.get("character_class", "")
    casting_ab = get_casting_ability(cls)
    if not casting_ab:
        return 0
    score = sheet.get("ability_scores", {}).get(casting_ab, 10)
    return proficiency_bonus(sheet.get("level", 1)) + ability_modifier(score)
