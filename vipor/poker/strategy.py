from collections import Counter
from dataclasses import dataclass
from typing import List, Callable
import random

from .cards import Card
from .paytable import PayTable
from .best_hold_mc import best_hold_mask_mc


@dataclass(frozen=True)
class HoldDecision:
    mask: int

def mask_from_indices(indices: List[int]) -> int:
    mask = 0
    for i in indices:
        mask |= 1 << i
    return mask

def hold_any_pair_else_none(cards: List[Card]) -> HoldDecision:
    counts = Counter(c.rank for c in cards)
    pairs = sorted((r for r, c in counts.items() if c == 2), reverse=True)
    if not pairs:
        return HoldDecision(0)

    target = pairs[0]
    mask = 0
    for i, c in enumerate(cards):
        if c.rank == target:
            mask |= 1 << i
    return HoldDecision(mask)


def hold_nothing(_cards: List[Card]) -> HoldDecision:
    return HoldDecision(0)


def make_mc_best_strategy(
    paytable: PayTable,
    seed: int | None,
    trials_per_mask: int,
    bet_per_hand: int,
) -> Callable[[List[Card]], HoldDecision]:
    rng = random.Random(seed)

    def _strategy(cards: List[Card]) -> HoldDecision:
        mask, _ev = best_hold_mask_mc(
            initial=cards,
            paytable=paytable,
            rng=rng,
            trials_per_mask=trials_per_mask,
            bet_per_hand=bet_per_hand,
        )
        return HoldDecision(mask)

    return _strategy

from .strategy_rules_riff import riff_strategy

