"""
effects.py -- D&D spell/area effect catalog for map overlays.

Each effect has a default shape, color, radius, and animation style.
DM places these on the map; they render on both DM and player views.
"""

# Shape types: "circle", "cone", "line", "cube"
# Animation types: None, "pulse", "flicker", "swirl"

EFFECT_CATALOG = {
    # -- Damage zones --
    "Fireball": {
        "shape": "circle",
        "radius": 4,  # 20ft = 4 squares
        "color": "#ff4500",
        "opacity": 0.35,
        "animation": "flicker",
        "category": "Damage",
    },
    "Lightning Bolt": {
        "shape": "line",
        "radius": 20,  # 100ft line = 20 squares
        "color": "#00bfff",
        "opacity": 0.4,
        "animation": "flicker",
        "category": "Damage",
    },
    "Burning Hands": {
        "shape": "cone",
        "radius": 3,  # 15ft cone = 3 squares
        "color": "#ff6600",
        "opacity": 0.35,
        "animation": "flicker",
        "category": "Damage",
    },
    "Cloud of Daggers": {
        "shape": "cube",
        "radius": 1,  # 5ft cube = 1 square
        "color": "#c0c0c0",
        "opacity": 0.4,
        "animation": "flicker",
        "category": "Damage",
    },
    "Moonbeam": {
        "shape": "circle",
        "radius": 1,  # 5ft radius cylinder
        "color": "#e6e6fa",
        "opacity": 0.35,
        "animation": "pulse",
        "category": "Damage",
    },
    "Spirit Guardians": {
        "shape": "circle",
        "radius": 3,  # 15ft radius
        "color": "#ffd700",
        "opacity": 0.35,
        "animation": "swirl",
        "category": "Damage",
    },
    "Spike Growth": {
        "shape": "circle",
        "radius": 4,  # 20ft radius
        "color": "#8b4513",
        "opacity": 0.3,
        "animation": None,
        "category": "Damage",
    },

    # -- Control / terrain --
    "Fog Cloud": {
        "shape": "circle",
        "radius": 4,  # 20ft radius
        "color": "#c8c8c8",
        "opacity": 0.5,
        "animation": "swirl",
        "category": "Control",
    },
    "Darkness": {
        "shape": "circle",
        "radius": 3,  # 15ft radius
        "color": "#1a0033",
        "opacity": 0.6,
        "animation": "pulse",
        "category": "Control",
    },
    "Silence": {
        "shape": "circle",
        "radius": 4,  # 20ft radius
        "color": "#6a6acc",
        "opacity": 0.4,
        "animation": "pulse",
        "category": "Control",
    },
    "Entangle": {
        "shape": "cube",
        "radius": 4,  # 20ft square
        "color": "#228b22",
        "opacity": 0.35,
        "animation": None,
        "category": "Control",
    },
    "Web": {
        "shape": "cube",
        "radius": 4,  # 20ft cube
        "color": "#f5f5f5",
        "opacity": 0.3,
        "animation": None,
        "category": "Control",
    },
    "Grease": {
        "shape": "cube",
        "radius": 2,  # 10ft square
        "color": "#9e8c6c",
        "opacity": 0.3,
        "animation": None,
        "category": "Control",
    },
    "Stinking Cloud": {
        "shape": "circle",
        "radius": 4,  # 20ft radius
        "color": "#9acd32",
        "opacity": 0.4,
        "animation": "swirl",
        "category": "Control",
    },
    "Sleet Storm": {
        "shape": "circle",
        "radius": 8,  # 40ft radius
        "color": "#b0e0e6",
        "opacity": 0.4,
        "animation": "swirl",
        "category": "Control",
    },
    "Plant Growth": {
        "shape": "circle",
        "radius": 20,  # 100ft radius
        "color": "#006400",
        "opacity": 0.35,
        "animation": None,
        "category": "Control",
    },
    "Hunger of Hadar": {
        "shape": "circle",
        "radius": 4,  # 20ft radius
        "color": "#0d001a",
        "opacity": 0.65,
        "animation": "pulse",
        "category": "Control",
    },

    # -- Walls / barriers --
    "Wall of Fire": {
        "shape": "line",
        "radius": 12,  # 60ft long
        "color": "#ff4500",
        "opacity": 0.45,
        "animation": "flicker",
        "category": "Wall",
    },
    "Wall of Force": {
        "shape": "line",
        "radius": 10,  # variable
        "color": "#87ceeb",
        "opacity": 0.45,
        "animation": "pulse",
        "category": "Wall",
    },
    "Wall of Thorns": {
        "shape": "line",
        "radius": 12,  # 60ft long
        "color": "#2e8b57",
        "opacity": 0.35,
        "animation": None,
        "category": "Wall",
    },
    "Blade Barrier": {
        "shape": "line",
        "radius": 20,  # 100ft long
        "color": "#c0c0c0",
        "opacity": 0.35,
        "animation": "flicker",
        "category": "Wall",
    },

    # -- Buffs / auras --
    "Bless": {
        "shape": "circle",
        "radius": 1,
        "color": "#ffd700",
        "opacity": 0.35,
        "animation": "pulse",
        "category": "Buff",
    },
    "Aura of Vitality": {
        "shape": "circle",
        "radius": 6,  # 30ft radius
        "color": "#00ff7f",
        "opacity": 0.35,
        "animation": "pulse",
        "category": "Buff",
    },
    "Antimagic Field": {
        "shape": "circle",
        "radius": 2,  # 10ft radius
        "color": "#a0a0d0",
        "opacity": 0.45,
        "animation": "pulse",
        "category": "Control",
    },

    # -- Hazards / environmental --
    "Bonfire": {
        "shape": "circle",
        "radius": 1,  # 5ft
        "color": "#ff6600",
        "opacity": 0.4,
        "animation": "flicker",
        "category": "Hazard",
    },
    "Lava": {
        "shape": "cube",
        "radius": 2,
        "color": "#ff2200",
        "opacity": 0.5,
        "animation": "flicker",
        "category": "Hazard",
    },
    "Poison Gas": {
        "shape": "circle",
        "radius": 3,
        "color": "#7cfc00",
        "opacity": 0.35,
        "animation": "swirl",
        "category": "Hazard",
    },
    "Ice": {
        "shape": "cube",
        "radius": 2,
        "color": "#add8e6",
        "opacity": 0.3,
        "animation": None,
        "category": "Hazard",
    },
    "Water (Deep)": {
        "shape": "cube",
        "radius": 3,
        "color": "#1e90ff",
        "opacity": 0.3,
        "animation": "swirl",
        "category": "Hazard",
    },
    "Rubble": {
        "shape": "cube",
        "radius": 2,
        "color": "#696969",
        "opacity": 0.35,
        "animation": None,
        "category": "Hazard",
    },
}


def get_categories():
    """Return sorted unique categories."""
    cats = sorted(set(e["category"] for e in EFFECT_CATALOG.values()))
    return cats


def get_effects_by_category():
    """Return {category: [effect_name, ...]} dict."""
    by_cat = {}
    for name, data in EFFECT_CATALOG.items():
        cat = data["category"]
        by_cat.setdefault(cat, []).append(name)
    for names in by_cat.values():
        names.sort()
    return by_cat
