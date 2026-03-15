"""Initiative tracker for the D&D virtual tabletop.

Provides initiative management functions that operate on an EncounterState.
"""

from __future__ import annotations
from typing import Dict, List

from core.dice import roll_initiative
from core.game_state import CreatureState, EncounterState


def roll_all_initiative(encounter: EncounterState, auto_roll_npcs: bool = True) -> List:
    """Roll initiative for creatures. If auto_roll_npcs, only auto-roll non-players."""
    results = []
    for creature in encounter.creatures:
        if auto_roll_npcs and creature.is_player:
            creature.initiative = float(creature.initiative_modifier)
        else:
            result = roll_creature_initiative(creature)
            results.append(result)
    return results


def roll_creature_initiative(creature: CreatureState):
    """Roll initiative for a single creature. Sets creature.initiative, returns DiceResult."""
    result = roll_initiative(creature.initiative_modifier, name=creature.name)
    creature.initiative = float(result.total)
    return result


def sort_initiative(encounter: EncounterState) -> None:
    """Sort creatures by initiative descending. Tiebreaker: higher modifier, then name."""
    encounter.creatures.sort(
        key=lambda c: (
            c.initiative if c.initiative is not None else -999.0,
            c.initiative_modifier,
            # Alphabetical ascending as final tiebreaker (negate via reverse)
        ),
        reverse=True,
    )


def start_combat(encounter: EncounterState) -> None:
    """Begin combat: sort initiative, reset round counter, and log."""
    sort_initiative(encounter)
    encounter.round_number = 1
    encounter.active_creature_index = 0
    encounter.combat_started = True
    encounter.log_event("combat_start", "Combat started -- Round 1")


def next_turn(encounter: EncounterState) -> CreatureState:
    """Advance to next living creature. Dead creatures are skipped."""
    num = len(encounter.creatures)
    if num == 0:
        raise ValueError("No creatures in the encounter")

    start = encounter.active_creature_index
    index = start
    wrapped = False

    while True:
        index += 1
        if index >= num:
            index = 0
            encounter.round_number += 1
            wrapped = True

        if wrapped and index == start:
            break

        creature = encounter.creatures[index]
        if "Dead" not in creature.conditions:
            encounter.active_creature_index = index
            encounter.log_event(
                "turn_start",
                f"{creature.name}'s turn (Round {encounter.round_number})",
                {"creature_id": creature.id},
            )
            return creature

    return encounter.creatures[encounter.active_creature_index]


def previous_turn(encounter: EncounterState) -> CreatureState:
    """Go back to previous living creature. Dead creatures are skipped."""
    num = len(encounter.creatures)
    if num == 0:
        raise ValueError("No creatures in the encounter")

    start = encounter.active_creature_index
    index = start
    wrapped = False

    while True:
        index -= 1
        if index < 0:
            index = num - 1
            encounter.round_number = max(1, encounter.round_number - 1)
            wrapped = True

        if wrapped and index == start:
            break

        creature = encounter.creatures[index]
        if "Dead" not in creature.conditions:
            encounter.active_creature_index = index
            encounter.log_event(
                "turn_back",
                f"Back to {creature.name}'s turn (Round {encounter.round_number})",
                {"creature_id": creature.id},
            )
            return creature

    return encounter.creatures[encounter.active_creature_index]


def get_turn_order_display(encounter: EncounterState) -> List[Dict]:
    """Build a list of dicts for UI display of the turn order."""
    display: List[Dict] = []
    for idx, creature in enumerate(encounter.creatures):
        display.append({
            "name": creature.name,
            "initiative": creature.initiative,
            "hp": creature.hp,
            "hp_max": creature.hp_max,
            "conditions": list(creature.conditions),
            "is_active": idx == encounter.active_creature_index,
            "is_player": creature.is_player,
            "creature_id": creature.id,
        })
    return display
