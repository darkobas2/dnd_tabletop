"""Utility for extracting readable creature names from token filenames.

Common patterns:
  _token-editor_token-uploads_humanoid_halforcfighter1_2026-03-15T12_59_00.900Z.png
  _token-editor_token-uploads_humanoid_humanbanditsniper1_timestamp.png
  goblin_warrior.png
  RedDragonWyrmling.png
"""

import re

# Known D&D race/class/creature words for splitting compound names
_KNOWN_WORDS = {
    # Races
    "human", "elf", "dwarf", "halfling", "gnome", "orc", "halforc", "halfelf",
    "tiefling", "dragonborn", "aasimar", "goliath", "tabaxi", "kenku", "goblin",
    "hobgoblin", "bugbear", "kobold", "lizardfolk", "firbolg", "genasi",
    "changeling", "shifter", "warforged", "tortle", "yuan", "githyanki",
    "githzerai", "triton", "minotaur", "centaur", "satyr", "fairy", "harengon",
    "drow", "eladrin",
    # Classes
    "fighter", "wizard", "rogue", "cleric", "ranger", "paladin", "barbarian",
    "bard", "druid", "monk", "sorcerer", "warlock", "artificer",
    # Creature types
    "bandit", "guard", "knight", "soldier", "archer", "sniper", "assassin",
    "captain", "chief", "warrior", "mage", "priest", "acolyte", "cultist",
    "skeleton", "zombie", "ghoul", "vampire", "werewolf", "ogre", "troll",
    "giant", "dragon", "wyrmling", "wyvern", "demon", "devil", "elemental",
    "golem", "beast", "wolf", "bear", "spider", "rat", "snake", "bat",
    "scout", "spy", "thug", "noble", "commoner", "veteran", "berserker",
    "gladiator", "necromancer", "lich", "wraith", "specter", "ghost",
    # Descriptors
    "young", "adult", "ancient", "red", "blue", "green", "black", "white",
    "gold", "silver", "bronze", "copper", "brass", "fire", "ice", "storm",
    "shadow", "dark", "light", "wild", "feral",
}

# Sort by length descending so longer matches take priority
_SORTED_WORDS = sorted(_KNOWN_WORDS, key=len, reverse=True)

# Display name overrides for compound words
_DISPLAY_NAMES = {
    "halforc": "Half-Orc",
    "halfelf": "Half-Elf",
    "yuan": "Yuan-Ti",
}


def extract_creature_name(filename: str) -> str:
    """Extract a readable creature name from a token filename.

    Examples:
        _token-editor_token-uploads_humanoid_halforcfighter1_2026-...png -> Half Orc Fighter
        goblin_warrior.png -> Goblin Warrior
        RedDragonWyrmling.png -> Red Dragon Wyrmling
        humanbanditsniper1 -> Human Bandit Sniper
    """
    # Strip extension
    name = filename.rsplit('.', 1)[0] if '.' in filename else filename

    # Remove common token-editor prefixes
    # Pattern: _token-editor_token-uploads_{category}_{actualname}_{timestamp}
    token_editor_match = re.search(r'token-uploads_\w+?_([a-zA-Z]+\d*?)_\d{4}', name)
    if token_editor_match:
        name = token_editor_match.group(1)
    else:
        # Try to get the last meaningful segment
        # Split on common separators
        parts = re.split(r'[_\-/\\]', name)
        # Filter out noise: timestamps, hashes, 'token', 'editor', 'uploads', etc.
        noise = {'token', 'editor', 'uploads', 'humanoid', 'beast', 'monstrosity',
                 'undead', 'fiend', 'celestial', 'fey', 'aberration', 'construct',
                 'ooze', 'plant', 'dragon', 'giant', 'elemental'}
        meaningful = []
        for p in parts:
            p_lower = p.lower().strip()
            if not p_lower:
                continue
            # Skip timestamps (contains T and digits)
            if re.match(r'\d{4}-\d{2}', p_lower) or re.match(r'\d{2}_\d{2}', p_lower):
                continue
            if re.match(r'^T?\d+[_:.]', p_lower):
                continue
            # Skip pure numbers
            if re.match(r'^\d+$', p_lower):
                continue
            if p_lower in noise and len(meaningful) > 0:
                continue
            if len(p_lower) > 2:
                meaningful.append(p)

        if meaningful:
            # Join all meaningful parts (e.g. "goblin_warrior" -> "goblin warrior")
            name = ' '.join(meaningful)

    # Remove trailing numbers
    name_clean = re.sub(r'\d+$', '', name.strip())
    if not name_clean:
        name_clean = name.strip()

    # If name has spaces/separators, split each word individually
    parts = re.split(r'[\s_\-]+', name_clean)
    result_parts = []
    for part in parts:
        if not part:
            continue
        split = _split_compound(part.lower())
        result_parts.append(split)

    return ' '.join(result_parts) if result_parts else name_clean.capitalize()


def _split_compound(text: str) -> str:
    """Split a compound word like 'halforcfighter' into 'Half Orc Fighter'."""
    # First try CamelCase splitting
    if any(c.isupper() for c in text[1:]):
        parts = re.findall(r'[A-Z][a-z]*|[a-z]+', text)
        if len(parts) > 1:
            return ' '.join(p.capitalize() for p in parts)

    # Try matching known words greedily
    remaining = text.lower()
    words = []

    while remaining:
        matched = False
        for word in _SORTED_WORDS:
            if remaining.startswith(word):
                display = _DISPLAY_NAMES.get(word, word.capitalize())
                words.append(display)
                remaining = remaining[len(word):]
                matched = True
                break

        if not matched:
            # Take one character and move on (handles unknown prefixes)
            # Try to grab a chunk until the next known word
            next_match = len(remaining)
            for word in _SORTED_WORDS:
                idx = remaining.find(word, 1)
                if idx > 0 and idx < next_match:
                    next_match = idx
            chunk = remaining[:next_match]
            if chunk:
                words.append(chunk.capitalize())
            remaining = remaining[next_match:]

    if words:
        return ' '.join(words)

    return text.capitalize()
