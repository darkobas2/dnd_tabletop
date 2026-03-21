"""
game_state.py — Single source of truth game state model for D&D Virtual Tabletop.

Phase 0.1: Pure Python, JSON-serializable, subprocess-safe.
No UI imports. All classes use dataclasses with to_dict()/from_dict() for
JSON round-tripping (used to pass state to the 3D Ursina subprocess via tempfile).
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# CreatureState
# ---------------------------------------------------------------------------

@dataclass
class CreatureState:
    """A single creature (PC, NPC, or monster) on the board."""

    name: str
    hp: int
    hp_max: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hp_temp: int = 0
    ac: int = 10
    speed: int = 30
    conditions: List[str] = field(default_factory=list)
    initiative: Optional[float] = None
    initiative_modifier: int = 0
    is_visible: bool = True
    is_player: bool = False
    size_category: str = "Medium"
    position: Tuple[int, int] = (0, 0)
    token_path: str = ""
    token_scale: float = 1.0
    notes: str = ""
    summoned_by: str = ""  # creature id of summoner, empty = not a summon
    summon_color: str = ""  # glow color for summoned creatures
    death_saves: Dict[str, int] = field(
        default_factory=lambda: {"successes": 0, "failures": 0}
    )

    # -- HP helpers --------------------------------------------------------

    def apply_damage(self, amount: int) -> None:
        """Reduce hp_temp first, then hp. Floor at 0.

        If a player creature drops to 0 hp, automatically add the
        ``Unconscious`` condition.
        """
        if amount <= 0:
            return

        if self.hp_temp > 0:
            absorbed = min(self.hp_temp, amount)
            self.hp_temp -= absorbed
            amount -= absorbed

        self.hp = max(self.hp - amount, 0)

        if self.hp == 0 and self.is_player:
            self.add_condition("Unconscious")

    def apply_healing(self, amount: int) -> None:
        """Increase hp, capped at hp_max.

        If healed from 0 hp, remove ``Unconscious`` and reset death saves.
        """
        if amount <= 0:
            return

        was_at_zero = self.hp == 0
        self.hp = min(self.hp + amount, self.hp_max)

        if was_at_zero and self.hp > 0:
            self.remove_condition("Unconscious")
            self.death_saves = {"successes": 0, "failures": 0}

    def set_hp(self, value: int) -> None:
        """Directly set current hp (clamped to [0, hp_max])."""
        self.hp = max(0, min(value, self.hp_max))

    # -- Condition helpers -------------------------------------------------

    def add_condition(self, condition: str) -> None:
        """Add a condition if not already present."""
        if condition not in self.conditions:
            self.conditions.append(condition)

    def remove_condition(self, condition: str) -> None:
        """Remove a condition if present."""
        if condition in self.conditions:
            self.conditions.remove(condition)

    # -- Death save helpers ------------------------------------------------

    def death_save_success(self) -> str:
        """Record a death save success. Returns status string."""
        self.death_saves["successes"] = min(
            self.death_saves["successes"] + 1, 3
        )
        if self.death_saves["successes"] >= 3:
            self.add_condition("Stable")
            self.remove_condition("Unconscious")
            return "stable"
        return "success"

    def death_save_failure(self) -> str:
        """Record a death save failure. Returns status string."""
        self.death_saves["failures"] = min(
            self.death_saves["failures"] + 1, 3
        )
        if self.death_saves["failures"] >= 3:
            self.add_condition("Dead")
            self.remove_condition("Unconscious")
            return "dead"
        return "failure"

    # -- Serialization -----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "hp": self.hp,
            "hp_max": self.hp_max,
            "hp_temp": self.hp_temp,
            "ac": self.ac,
            "speed": self.speed,
            "conditions": list(self.conditions),
            "initiative": self.initiative,
            "initiative_modifier": self.initiative_modifier,
            "is_visible": self.is_visible,
            "is_player": self.is_player,
            "size_category": self.size_category,
            "position": list(self.position),
            "token_path": self.token_path,
            "token_scale": self.token_scale,
            "notes": self.notes,
            "summoned_by": self.summoned_by,
            "summon_color": self.summon_color,
            "death_saves": dict(self.death_saves),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CreatureState:
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d["name"],
            hp=d["hp"],
            hp_max=d["hp_max"],
            hp_temp=d.get("hp_temp", 0),
            ac=d.get("ac", 10),
            speed=d.get("speed", 30),
            conditions=list(d.get("conditions", [])),
            initiative=d.get("initiative"),
            initiative_modifier=d.get("initiative_modifier", 0),
            is_visible=d.get("is_visible", True),
            is_player=d.get("is_player", False),
            size_category=d.get("size_category", "Medium"),
            position=tuple(d.get("position", [0, 0])),
            token_path=d.get("token_path", ""),
            token_scale=d.get("token_scale", 1.0),
            notes=d.get("notes", ""),
            summoned_by=d.get("summoned_by", ""),
            summon_color=d.get("summon_color", ""),
            death_saves=d.get(
                "death_saves", {"successes": 0, "failures": 0}
            ),
        )


# ---------------------------------------------------------------------------
# MapEffect
# ---------------------------------------------------------------------------

@dataclass
class MapEffect:
    """A visual area effect placed on the map (spell, hazard, etc.)."""

    name: str
    shape: str  # "circle", "cone", "line", "cube"
    position: Tuple[float, float] = (0.0, 0.0)  # grid coords (center)
    radius: int = 4  # size in grid squares
    color: str = "#ff4500"
    opacity: float = 0.35
    animation: Optional[str] = None  # None, "pulse", "flicker", "swirl"
    rotation: float = 0.0  # degrees, for cone/line direction
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    visible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "shape": self.shape,
            "position": list(self.position),
            "radius": self.radius,
            "color": self.color,
            "opacity": self.opacity,
            "animation": self.animation,
            "rotation": self.rotation,
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MapEffect:
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Effect"),
            shape=d.get("shape", "circle"),
            position=tuple(d.get("position", [0.0, 0.0])),
            radius=d.get("radius", 4),
            color=d.get("color", "#ff4500"),
            opacity=d.get("opacity", 0.35),
            animation=d.get("animation"),
            rotation=d.get("rotation", 0.0),
            visible=d.get("visible", True),
        )


# ---------------------------------------------------------------------------
# DiceResult
# ---------------------------------------------------------------------------

@dataclass
class DiceResult:
    """Result of a parsed dice expression like ``2d6+1d4+3``."""

    expression: str
    individual_rolls: List[List[int]]
    total: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    roller: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expression": self.expression,
            "individual_rolls": [list(g) for g in self.individual_rolls],
            "total": self.total,
            "timestamp": self.timestamp,
            "roller": self.roller,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DiceResult:
        return cls(
            expression=d["expression"],
            individual_rolls=[list(g) for g in d["individual_rolls"]],
            total=d["total"],
            timestamp=d.get(
                "timestamp", datetime.now(timezone.utc).isoformat()
            ),
            roller=d.get("roller", ""),
        )


# ---------------------------------------------------------------------------
# EncounterState
# ---------------------------------------------------------------------------

@dataclass
class EncounterState:
    """Full state of a single encounter / combat session."""

    creatures: List[CreatureState] = field(default_factory=list)
    effects: List[MapEffect] = field(default_factory=list)
    round_number: int = 0
    active_creature_index: int = -1
    combat_started: bool = False
    combat_log: List[Dict[str, Any]] = field(default_factory=list)
    fog_of_war: Optional[List[List[bool]]] = None

    # -- Creature management -----------------------------------------------

    def add_creature(self, creature: CreatureState) -> None:
        """Add a creature to the encounter."""
        self.creatures.append(creature)

    def remove_creature(self, creature_id: str) -> None:
        """Remove a creature by id.

        Adjusts ``active_creature_index`` so the turn order stays consistent.
        """
        for i, c in enumerate(self.creatures):
            if c.id == creature_id:
                self.creatures.pop(i)
                # Fix up active index after removal
                if self.combat_started and len(self.creatures) > 0:
                    if i < self.active_creature_index:
                        self.active_creature_index -= 1
                    elif i == self.active_creature_index:
                        # Current creature removed — index now points at next
                        if self.active_creature_index >= len(self.creatures):
                            self.active_creature_index = 0
                            self.round_number += 1
                elif len(self.creatures) == 0:
                    self.active_creature_index = -1
                    self.combat_started = False
                return

    def get_creature(self, creature_id: str) -> Optional[CreatureState]:
        """Look up a creature by id."""
        for c in self.creatures:
            if c.id == creature_id:
                return c
        return None

    # -- Effect management -------------------------------------------------

    def add_effect(self, effect: MapEffect) -> None:
        self.effects.append(effect)

    def remove_effect(self, effect_id: str) -> None:
        self.effects = [e for e in self.effects if e.id != effect_id]

    def get_effect(self, effect_id: str) -> Optional[MapEffect]:
        for e in self.effects:
            if e.id == effect_id:
                return e
        return None

    # -- Initiative / combat flow ------------------------------------------

    def start_combat(self) -> None:
        """Sort creatures by initiative (desc) and begin round 1."""
        self.creatures.sort(
            key=lambda c: (
                c.initiative if c.initiative is not None else -999.0
            ),
            reverse=True,
        )
        self.round_number = 1
        self.active_creature_index = 0
        self.combat_started = True
        self.log_event("combat_start", "Combat started — Round 1")

    def next_turn(self) -> None:
        """Advance to the next creature. Wrapping increments the round."""
        if not self.combat_started or not self.creatures:
            return
        self.active_creature_index += 1
        if self.active_creature_index >= len(self.creatures):
            self.active_creature_index = 0
            self.round_number += 1
            self.log_event(
                "new_round", f"Round {self.round_number} begins"
            )
        active = self.get_active_creature()
        if active:
            self.log_event(
                "turn_start",
                f"{active.name}'s turn",
                {"creature_id": active.id},
            )

    def previous_turn(self) -> None:
        """Go back to the previous creature. Wrapping decrements the round."""
        if not self.combat_started or not self.creatures:
            return
        self.active_creature_index -= 1
        if self.active_creature_index < 0:
            self.active_creature_index = len(self.creatures) - 1
            self.round_number = max(self.round_number - 1, 1)

    def get_active_creature(self) -> Optional[CreatureState]:
        """Return the creature whose turn it currently is."""
        if (
            not self.combat_started
            or not self.creatures
            or self.active_creature_index < 0
            or self.active_creature_index >= len(self.creatures)
        ):
            return None
        return self.creatures[self.active_creature_index]

    def get_initiative_order(self) -> List[CreatureState]:
        """Return creatures sorted by initiative descending."""
        return sorted(
            self.creatures,
            key=lambda c: (
                c.initiative if c.initiative is not None else -999.0
            ),
            reverse=True,
        )

    # -- Combat log --------------------------------------------------------

    def log_event(
        self,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a timestamped entry to the combat log."""
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "message": message,
            "round": self.round_number,
        }
        if details:
            entry["details"] = details
        self.combat_log.append(entry)

    # -- Fog of war --------------------------------------------------------

    def init_fog(self, width: int, height: int) -> None:
        """Create a fog-of-war grid (all cells hidden / ``False``)."""
        self.fog_of_war = [
            [False for _ in range(width)] for _ in range(height)
        ]

    def reveal_fog(self, x: int, y: int, radius: int = 1) -> None:
        """Reveal cells within *radius* of (x, y) using Euclidean distance."""
        if self.fog_of_war is None:
            return
        height = len(self.fog_of_war)
        if height == 0:
            return
        width = len(self.fog_of_war[0])

        for ry in range(max(0, y - radius), min(height, y + radius + 1)):
            for rx in range(max(0, x - radius), min(width, x + radius + 1)):
                if math.hypot(rx - x, ry - y) <= radius:
                    self.fog_of_war[ry][rx] = True

    # -- Serialization -----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "creatures": [c.to_dict() for c in self.creatures],
            "effects": [e.to_dict() for e in self.effects],
            "round_number": self.round_number,
            "active_creature_index": self.active_creature_index,
            "combat_started": self.combat_started,
            "combat_log": list(self.combat_log),
            "fog_of_war": (
                [list(row) for row in self.fog_of_war]
                if self.fog_of_war is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EncounterState:
        fog = d.get("fog_of_war")
        if fog is not None:
            fog = [list(row) for row in fog]
        return cls(
            creatures=[
                CreatureState.from_dict(c) for c in d.get("creatures", [])
            ],
            effects=[
                MapEffect.from_dict(e) for e in d.get("effects", [])
            ],
            round_number=d.get("round_number", 0),
            active_creature_index=d.get("active_creature_index", -1),
            combat_started=d.get("combat_started", False),
            combat_log=list(d.get("combat_log", [])),
            fog_of_war=fog,
        )
