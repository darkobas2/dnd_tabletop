"""D&D 5e conditions with colors and icons for UI display."""

CONDITIONS = {
    "Blinded": "A blinded creature can't see and automatically fails any ability check that requires sight.",
    "Charmed": "A charmed creature can't attack the charmer or target the charmer with harmful abilities or magical effects.",
    "Deafened": "A deafened creature can't hear and automatically fails any ability check that requires hearing.",
    "Exhaustion": "Exhaustion effects are cumulative. Levels stack.",
    "Frightened": "A frightened creature has disadvantage on ability checks and attack rolls while the source of its fear is within line of sight.",
    "Grappled": "A grappled creature's speed becomes 0, and it can't benefit from any bonus to its speed.",
    "Incapacitated": "An incapacitated creature can't take actions or reactions.",
    "Invisible": "An invisible creature is impossible to see without the aid of magic or a special sense.",
    "Paralyzed": "A paralyzed creature is incapacitated and can't move or speak. Auto-fails Str/Dex saves. Attacks have advantage, melee crits.",
    "Petrified": "A petrified creature is transformed into a solid inanimate substance. Weight increases x10.",
    "Poisoned": "A poisoned creature has disadvantage on attack rolls and ability checks.",
    "Prone": "A prone creature's only movement option is to crawl. Disadvantage on attacks. Melee attacks have advantage against it.",
    "Restrained": "A restrained creature's speed becomes 0. Attack rolls against it have advantage. Its attacks have disadvantage.",
    "Stunned": "A stunned creature is incapacitated, can't move, and can speak only falteringly.",
    "Unconscious": "An unconscious creature is incapacitated, can't move or speak, drops what it's holding, and falls prone.",
    "Concentrating": "Maintaining concentration on a spell. Taking damage requires a Constitution saving throw.",
    "Dead": "The creature has died.",
    "Stable": "The creature is stable at 0 HP and no longer makes death saving throws.",
}

CONDITION_COLORS = {
    "Blinded": "#4a4a4a",
    "Charmed": "#ff69b4",
    "Deafened": "#808080",
    "Exhaustion": "#8b4513",
    "Frightened": "#9b59b6",
    "Grappled": "#e67e22",
    "Incapacitated": "#7f8c8d",
    "Invisible": "#3498db",
    "Paralyzed": "#f1c40f",
    "Petrified": "#95a5a6",
    "Poisoned": "#27ae60",
    "Prone": "#d35400",
    "Restrained": "#c0392b",
    "Stunned": "#f39c12",
    "Unconscious": "#2c3e50",
    "Concentrating": "#2980b9",
    "Dead": "#000000",
    "Stable": "#1abc9c",
}

CONDITION_ICONS = {
    "Blinded": "\U0001f441",
    "Charmed": "\u2764",
    "Deafened": "\U0001f507",
    "Exhaustion": "\u2b07",
    "Frightened": "\u2620",
    "Grappled": "\U0001f91d",
    "Incapacitated": "\U0001f4ab",
    "Invisible": "\U0001f47b",
    "Paralyzed": "\u26a1",
    "Petrified": "\U0001f5ff",
    "Poisoned": "\u2622",
    "Prone": "\u2b07",
    "Restrained": "\u26d3",
    "Stunned": "\U0001f4a5",
    "Unconscious": "\U0001f4a4",
    "Concentrating": "\U0001f52e",
    "Dead": "\U0001f480",
    "Stable": "\U0001f49a",
}


def get_condition_info(name: str) -> dict:
    """Get full info for a condition."""
    return {
        "name": name,
        "description": CONDITIONS.get(name, "Unknown condition"),
        "color": CONDITION_COLORS.get(name, "#aaaaaa"),
        "icon": CONDITION_ICONS.get(name, "?"),
    }
