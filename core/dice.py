"""Dice engine for the D&D virtual tabletop.

Parses and evaluates dice expressions such as:
    "2d6+3"       - roll 2d6 and add 3
    "1d20+5"      - standard ability check
    "4d6kh3"      - roll 4d6 keep highest 3 (ability score generation)
    "2d20kl1"     - roll 2d20 keep lowest 1 (disadvantage)
    "1d20adv"     - advantage (shorthand for 2d20kh1)
    "1d20dis"     - disadvantage (shorthand for 2d20kl1)
    "2d6+1d4+3"   - mixed expression with multiple dice groups
"""

import random
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from core.game_state import DiceResult


@dataclass
class DiceGroup:
    """A single dice term, e.g. '4d6kh3'."""
    count: int
    sides: int
    keep_highest: Optional[int] = None
    keep_lowest: Optional[int] = None

    def roll(self) -> Tuple[List[int], List[int]]:
        """Roll this group and return (all_rolls, kept_rolls)."""
        rolls = sorted(
            [random.randint(1, self.sides) for _ in range(self.count)],
            reverse=True,
        )
        if self.keep_highest is not None:
            kept = rolls[:self.keep_highest]
        elif self.keep_lowest is not None:
            kept = rolls[-self.keep_lowest:]
        else:
            kept = list(rolls)
        return rolls, kept


# Regex for a single dice term
_DICE_RE = re.compile(
    r"(\d*)d(\d+)"
    r"(?:(kh|kl)(\d+))?"
    r"(adv|dis)?",
    re.IGNORECASE,
)


def parse_expression(expression: str) -> Tuple[List[DiceGroup], int]:
    """Parse a dice expression into DiceGroups and a flat modifier."""
    expr = expression.strip().lower().replace(" ", "")
    groups: List[DiceGroup] = []
    modifier = 0

    tokens = re.split(r"(?=[+-])", "+" + expr)

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        sign = 1
        if token.startswith("-"):
            sign = -1
            token = token[1:]
        elif token.startswith("+"):
            token = token[1:]

        if not token:
            continue

        m = _DICE_RE.fullmatch(token)
        if m:
            count = int(m.group(1)) if m.group(1) else 1
            sides = int(m.group(2))
            keep_highest: Optional[int] = None
            keep_lowest: Optional[int] = None

            if m.group(3):
                k_value = int(m.group(4))
                if m.group(3) == "kh":
                    keep_highest = k_value
                else:
                    keep_lowest = k_value

            if m.group(5):
                count = 2
                if m.group(5) == "adv":
                    keep_highest = 1
                else:
                    keep_lowest = 1

            g = DiceGroup(count=count, sides=sides,
                          keep_highest=keep_highest, keep_lowest=keep_lowest)
            g._sign = sign  # type: ignore[attr-defined]
            groups.append(g)
        else:
            try:
                modifier += sign * int(token)
            except ValueError:
                raise ValueError(f"Unrecognised token '{token}' in expression '{expression}'")

    return groups, modifier


def roll_dice(expression: str, roller: str = "") -> DiceResult:
    """Parse expression, roll every group, return a DiceResult."""
    groups, modifier = parse_expression(expression)

    individual_rolls: List[List[int]] = []
    total = modifier

    for g in groups:
        rolls, kept = g.roll()
        sign: int = getattr(g, "_sign", 1)
        individual_rolls.append(kept)
        total += sign * sum(kept)

    return DiceResult(
        expression=expression,
        individual_rolls=individual_rolls,
        total=total,
        roller=roller,
    )


def quick_roll(sides: int, count: int = 1, modifier: int = 0) -> DiceResult:
    """Convenience wrapper for simple rolls like '1d20+5'."""
    mod_str = ""
    if modifier > 0:
        mod_str = f"+{modifier}"
    elif modifier < 0:
        mod_str = str(modifier)
    return roll_dice(f"{count}d{sides}{mod_str}")


def roll_initiative(modifier: int = 0, name: str = "") -> DiceResult:
    """Roll initiative (1d20 + modifier)."""
    mod_str = ""
    if modifier > 0:
        mod_str = f"+{modifier}"
    elif modifier < 0:
        mod_str = str(modifier)
    return roll_dice(f"1d20{mod_str}", roller=name)
