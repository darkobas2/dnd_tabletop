"""
summons.py -- Catalog of D&D summonable creatures, conjured objects, and familiars.

Each entry has a default stat block and visual settings. DM picks a summoner
(player character) when placing, and the summon is linked to that character.
"""

SUMMON_CATALOG = {
    # ---- Familiars & Companions ----
    "Cat (Familiar)": {
        "hp": 2, "ac": 12, "speed": 40,
        "size": "Tiny", "color": "#a0522d",
        "category": "Familiar",
    },
    "Owl (Familiar)": {
        "hp": 1, "ac": 11, "speed": 60,
        "size": "Tiny", "color": "#d2b48c",
        "category": "Familiar",
    },
    "Raven (Familiar)": {
        "hp": 1, "ac": 12, "speed": 50,
        "size": "Tiny", "color": "#2f2f2f",
        "category": "Familiar",
    },
    "Hawk (Familiar)": {
        "hp": 1, "ac": 13, "speed": 60,
        "size": "Tiny", "color": "#8b6914",
        "category": "Familiar",
    },
    "Spider (Familiar)": {
        "hp": 1, "ac": 12, "speed": 20,
        "size": "Tiny", "color": "#4a4a4a",
        "category": "Familiar",
    },
    "Bat (Familiar)": {
        "hp": 1, "ac": 12, "speed": 30,
        "size": "Tiny", "color": "#3d3d3d",
        "category": "Familiar",
    },
    "Pseudodragon": {
        "hp": 7, "ac": 13, "speed": 15,
        "size": "Tiny", "color": "#c41e3a",
        "category": "Familiar",
    },
    "Imp": {
        "hp": 10, "ac": 13, "speed": 20,
        "size": "Tiny", "color": "#8b0000",
        "category": "Familiar",
    },
    "Quasit": {
        "hp": 7, "ac": 13, "speed": 40,
        "size": "Tiny", "color": "#556b2f",
        "category": "Familiar",
    },

    # ---- Conjured Weapons / Objects ----
    "Spiritual Weapon": {
        "hp": 999, "ac": 99, "speed": 20,
        "size": "Medium", "color": "#ffd700",
        "category": "Conjured",
        "notes": "Bonus action to attack: spell mod + d8 force",
    },
    "Mage Hand": {
        "hp": 999, "ac": 99, "speed": 30,
        "size": "Medium", "color": "#87ceeb",
        "category": "Conjured",
        "notes": "Spectral hand, can manipulate objects up to 10 lb",
    },
    "Bigby's Hand": {
        "hp": 999, "ac": 20, "speed": 60,
        "size": "Large", "color": "#daa520",
        "category": "Conjured",
        "notes": "Large spectral hand, multiple attack/grapple modes",
    },
    "Flaming Sphere": {
        "hp": 999, "ac": 99, "speed": 30,
        "size": "Medium", "color": "#ff4500",
        "category": "Conjured",
        "notes": "2d6 fire on adjacent creatures, bonus action to move",
    },
    "Dancing Sword": {
        "hp": 999, "ac": 99, "speed": 30,
        "size": "Small", "color": "#c0c0c0",
        "category": "Conjured",
        "notes": "Bonus action to move and attack",
    },
    "Unseen Servant": {
        "hp": 1, "ac": 10, "speed": 15,
        "size": "Medium", "color": "#b0c4de",
        "category": "Conjured",
        "notes": "Invisible force, simple tasks only",
    },
    "Mordenkainen's Sword": {
        "hp": 999, "ac": 99, "speed": 30,
        "size": "Medium", "color": "#e6e6fa",
        "category": "Conjured",
        "notes": "3d10 force damage, bonus action to move and attack",
    },

    # ---- Summoned Beasts ----
    "Wolf": {
        "hp": 11, "ac": 13, "speed": 40,
        "size": "Medium", "color": "#808080",
        "category": "Beast",
    },
    "Giant Spider": {
        "hp": 26, "ac": 14, "speed": 30,
        "size": "Large", "color": "#2f4f4f",
        "category": "Beast",
    },
    "Bear (Black)": {
        "hp": 19, "ac": 11, "speed": 40,
        "size": "Medium", "color": "#3b2f2f",
        "category": "Beast",
    },
    "Giant Eagle": {
        "hp": 26, "ac": 13, "speed": 80,
        "size": "Large", "color": "#cd853f",
        "category": "Beast",
    },
    "Dire Wolf": {
        "hp": 37, "ac": 14, "speed": 50,
        "size": "Large", "color": "#696969",
        "category": "Beast",
    },
    "Giant Elk": {
        "hp": 42, "ac": 14, "speed": 60,
        "size": "Huge", "color": "#8b7355",
        "category": "Beast",
    },

    # ---- Elementals ----
    "Fire Elemental": {
        "hp": 102, "ac": 13, "speed": 50,
        "size": "Large", "color": "#ff4500",
        "category": "Elemental",
    },
    "Water Elemental": {
        "hp": 114, "ac": 14, "speed": 30,
        "size": "Large", "color": "#4169e1",
        "category": "Elemental",
    },
    "Earth Elemental": {
        "hp": 126, "ac": 17, "speed": 30,
        "size": "Large", "color": "#8b7355",
        "category": "Elemental",
    },
    "Air Elemental": {
        "hp": 90, "ac": 15, "speed": 90,
        "size": "Large", "color": "#b0e0e6",
        "category": "Elemental",
    },

    # ---- Undead Summons ----
    "Skeleton": {
        "hp": 13, "ac": 13, "speed": 30,
        "size": "Medium", "color": "#d3d3bc",
        "category": "Undead",
    },
    "Zombie": {
        "hp": 22, "ac": 8, "speed": 20,
        "size": "Medium", "color": "#556b2f",
        "category": "Undead",
    },
    "Shadow": {
        "hp": 16, "ac": 12, "speed": 40,
        "size": "Medium", "color": "#1a1a2e",
        "category": "Undead",
    },
    "Specter": {
        "hp": 22, "ac": 12, "speed": 50,
        "size": "Medium", "color": "#4a4a6a",
        "category": "Undead",
    },

    # ---- Fey / Celestial ----
    "Pixie": {
        "hp": 1, "ac": 15, "speed": 10,
        "size": "Tiny", "color": "#ff69b4",
        "category": "Fey",
    },
    "Sprite": {
        "hp": 2, "ac": 15, "speed": 10,
        "size": "Tiny", "color": "#90ee90",
        "category": "Fey",
    },
    "Dryad": {
        "hp": 22, "ac": 11, "speed": 30,
        "size": "Medium", "color": "#228b22",
        "category": "Fey",
    },
    "Celestial Spirit": {
        "hp": 40, "ac": 16, "speed": 30,
        "size": "Large", "color": "#fffacd",
        "category": "Fey",
    },
}

# Size to token scale mapping
SIZE_SCALES = {
    "Tiny": 0.5,
    "Small": 0.7,
    "Medium": 1.0,
    "Large": 1.4,
    "Huge": 2.0,
    "Gargantuan": 3.0,
}


def get_summon_categories():
    """Return sorted unique categories."""
    return sorted(set(s["category"] for s in SUMMON_CATALOG.values()))


def get_summons_by_category():
    """Return {category: [name, ...]} dict."""
    by_cat = {}
    for name, data in SUMMON_CATALOG.items():
        cat = data["category"]
        by_cat.setdefault(cat, []).append(name)
    for names in by_cat.values():
        names.sort()
    return by_cat
