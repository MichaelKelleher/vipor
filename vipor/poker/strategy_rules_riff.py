from __future__ import annotations

from typing import List

from .cards import Card
from .hand_eval import (
    ROYAL_FLUSH,
    STRAIGHT_FLUSH,
    FOUR,
    FULL_HOUSE,
    FLUSH,
    STRAIGHT,
    THREE,
    TWO_PAIR,
    evaluate_hand,
)
from .strategy import HoldDecision
from .strategy_helpers import (
    ROYAL_RANKS,
    best_pair_indices,
    job_pair_indices,
    mask_from_indices,
    n_to_flush,
    n_to_royal,
    pair_ranks,
)


def _hold_all() -> HoldDecision:
    return HoldDecision(31)


def riff_strategy(cards: List[Card]) -> HoldDecision:
    cat = evaluate_hand(cards).category

    # Made hands: always hold all 5 (for JoB / no kickers)
    if cat in (ROYAL_FLUSH, STRAIGHT_FLUSH, FOUR, FULL_HOUSE, FLUSH, STRAIGHT, THREE):
        return _hold_all()

    # Draws
    idx = n_to_royal(cards, 4)
    if idx:
        return HoldDecision(mask_from_indices(idx))

    idx = n_to_royal(cards, 3)
    if idx:
        return HoldDecision(mask_from_indices(idx))

    idx = n_to_flush(cards, 4)
    if idx:
        return HoldDecision(mask_from_indices(idx))

    # Pairs
    pairs = pair_ranks(cards)
    # 2) Prefer low pairs 2–4 (choose the lowest if multiple)
    if 14 in pairs:  # pair of aces
        idx = [i for i, c in enumerate(cards) if c.rank == 14]
        return HoldDecision(mask_from_indices(idx))

    low_35 = [r for r in pairs if 2 <= r <= 4]
    if low_35:
        keep_rank = min(low_35)
        return HoldDecision(mask_from_indices(counts[keep_rank]))
    
    idx = job_pair_indices(cards)
    if idx:
        return HoldDecision(mask_from_indices(idx))

    if cat == TWO_PAIR:
        ranks = set(pair_ranks(cards))
        idx = [i for i, c in enumerate(cards) if c.rank in ranks]
        return HoldDecision(mask_from_indices(idx))

    idx = best_pair_indices(cards)
    if idx:
        return HoldDecision(mask_from_indices(idx))

    # Any royal ranks fallback
    idx = [i for i, c in enumerate(cards) if c.rank in ROYAL_RANKS]
    if idx:
        return HoldDecision(mask_from_indices(idx))

    return HoldDecision(0)

