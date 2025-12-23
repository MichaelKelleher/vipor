# vipor/poker/strategy_rules_j_riff_deuces_wild_bonus.py
from __future__ import annotations

from typing import List

from .cards import Card
from .hand_eval import (
    # These names may differ in your codebase. Adjust to match your Deuces evaluator.
    # The important part is: treat "made hands worth holding" as always-hold.
    ROYAL_FLUSH,
    STRAIGHT_FLUSH,
    FOUR,
    FULL_HOUSE,
    FLUSH,
    STRAIGHT,
    THREE,
    evaluate_hand,
)
from .strategy_helpers import (
    ROYAL_RANKS,
    mask_from_indices,
    n_to_flush,
    n_to_royal,
)
from .hold import HoldDecision



DEUCE_RANK = 2


def _hold_all() -> HoldDecision:
    return HoldDecision(31)


def _idxs(cards: List[Card], pred) -> List[int]:
    return [i for i, c in enumerate(cards) if pred(c)]


def j_riff_strategy_deuces_wild_bonus(cards: List[Card]) -> HoldDecision:
    """
    Deterministic j_riff strategy for Deuces Wild Bonus (first-pass).
    Goal: never hold random trash kickers; prioritize deuces and premium draws.
    """
    deuce_idx = _idxs(cards, lambda c: c.rank == DEUCE_RANK)
    d = len(deuce_idx)

    # --- 0) If you have any deuces, default posture is "keep deuces"
    # We'll upgrade to "deuces + premium draw" below.
    if d == 4:
        return _hold_all()

    # If your evaluator already understands wilds, made-hand categories are safe to hold-all.
    # (This catches things like natural/wild royals, five-of-kind, etc. if your eval maps them.)
    cat = evaluate_hand(cards).category
    if cat in (ROYAL_FLUSH, STRAIGHT_FLUSH, FOUR, FULL_HOUSE, FLUSH, STRAIGHT, THREE):
        return _hold_all()

    # Work with non-deuces for draw detection
    non_deuce_cards = [c for c in cards if c.rank != DEUCE_RANK]
    non_deuce_idx = [i for i, c in enumerate(cards) if c.rank != DEUCE_RANK]

    # Helper: convert indices found in the filtered list back to original indices
    def lift(filtered_indices: List[int]) -> List[int]:
        return [non_deuce_idx[i] for i in filtered_indices]

    # --- 1) Premium royal draws, "deuce-assisted"
    # With 1 deuce: 3-to-royal + deuce is "effectively" 4-to-royal
    # With 2 deuces: 2-to-royal + deuces is "effectively" 4-to-royal, etc.
    if d >= 1:
        k = 4 - d  # how many natural royal cards we need alongside deuces
        if k >= 2:
            idx = n_to_royal(non_deuce_cards, k)
            if idx:
                hold = lift(idx) + deuce_idx
                return HoldDecision(mask_from_indices(hold))

    # Always still take natural 4-to-royal if present (even with no deuces)
    idx = n_to_royal(non_deuce_cards, 4)
    if idx:
        return HoldDecision(mask_from_indices(lift(idx) + deuce_idx))

    # Natural 3-to-royal (no deuces): keep it (you did this in JoB)
    idx = n_to_royal(non_deuce_cards, 3)
    if idx:
        return HoldDecision(mask_from_indices(lift(idx) + deuce_idx))

    # --- 2) Flush draws, "deuce-assisted"
    # With d deuces, you only need (4 - d) suited natural cards to have a 4-flush draw.
    if d >= 1:
        k = 4 - d
        if k >= 2:
            idx = n_to_flush(non_deuce_cards, k)
            if idx:
                hold = lift(idx) + deuce_idx
                return HoldDecision(mask_from_indices(hold))

    # Natural 4-flush (or 3-flush if you want it; start conservative with 4)
    idx = n_to_flush(non_deuce_cards, 4)
    if idx:
        return HoldDecision(mask_from_indices(lift(idx) + deuce_idx))

    # --- 3) If any deuces remain and we didn't find a premium draw, just hold the deuces.
    if d > 0:
        return HoldDecision(mask_from_indices(deuce_idx))

    # --- 4) No deuces: fallback behavior similar to your JoB "royal ranks" bias
    hi_royal_idx = _idxs(cards, lambda c: c.rank in ROYAL_RANKS)
    if hi_royal_idx:
        return HoldDecision(mask_from_indices(hi_royal_idx))

    return HoldDecision(0)

