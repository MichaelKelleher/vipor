from __future__ import annotations

from typing import Callable, Dict, List

from .cards import Card
from .hold import HoldDecision
from .strategy_rules_j_riff import j_riff_strategy_deuces_wild_bonus


StrategyFn = Callable[[List[Card]], HoldDecision]

def hold_nothing(_cards: List[Card]) -> HoldDecision:
    return HoldDecision(mask=0)

def hold_all(_cards: List[Card]) -> HoldDecision:
    return HoldDecision(mask=31)

def hold_any_pair_else_none(cards: List[Card]) -> HoldDecision:
    counts: Dict[int, int] = {}
    for c in cards:
        counts[c.rank] = counts.get(c.rank, 0) + 1

    pair_ranks = {r for r, n in counts.items() if n >= 2}
    if not pair_ranks:
        return HoldDecision(mask=0)

    mask = 0
    for i, c in enumerate(cards):
        if c.rank in pair_ranks:
            mask |= (1 << i)
    return HoldDecision(mask=mask)

def hold_job_pair_else_none(cards: List[Card]) -> HoldDecision:
    counts: Dict[int, int] = {}
    for c in cards:
        counts[c.rank] = counts.get(c.rank, 0) + 1

    high_pair_ranks = {r for r, n in counts.items() if n >= 2 and r >= 11}
    if not high_pair_ranks:
        return HoldDecision(mask=0)

    mask = 0
    for i, c in enumerate(cards):
        if c.rank in high_pair_ranks:
            mask |= (1 << i)
    return HoldDecision(mask=mask)

STRATEGY_REGISTRY: Dict[str, StrategyFn] = {
    "none": hold_nothing,
    "all": hold_all,
    "any_pair": hold_any_pair_else_none,
    "job_pair": hold_job_pair_else_none,
    "j_riff_deuces_bonus": j_riff_strategy_deuces_wild_bonus,
}

# Optional strategies (do not let them break imports)
try:
    from .strategy_rules_j_riff import j_riff_strategy_deuces_wild_bonus
    STRATEGY_REGISTRY["j_riff_deuces_bonus"] = j_riff_strategy_deuces_wild_bonus
except Exception:
    pass

