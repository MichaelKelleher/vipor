import random
from typing import List, Tuple

from .cards import Card, RANKS, SUITS
from .hand_eval import evaluate_hand
from .paytable import PayTable


# Build a canonical 52-card deck once
FULL_DECK: List[Card] = [Card(rank=r, suit=s) for s in SUITS for r in RANKS]


def apply_hold_and_draw_from_sample(
    initial: List[Card],
    hold_mask: int,
    drawn: List[Card],
) -> List[Card]:
    """Fill non-held positions (in order) with cards from drawn."""
    final = initial[:]
    di = 0
    for i in range(5):
        if not (hold_mask & (1 << i)):
            final[i] = drawn[di]
            di += 1
    return final


def expected_payout_mc(
    initial: List[Card],
    hold_mask: int,
    paytable: PayTable,
    rng: random.Random,
    trials: int,
    bet_per_hand: int = 1,
) -> float:
    # Precompute remaining cards once per hand
    dealt = set(initial)
    remaining = [c for c in FULL_DECK if c not in dealt]

    draw_n = 5 - ((hold_mask & 0b00001) > 0) - ((hold_mask & 0b00010) > 0) - ((hold_mask & 0b00100) > 0) - ((hold_mask & 0b01000) > 0) - ((hold_mask & 0b10000) > 0)
    # (above avoids looping per trial; tiny micro-opt)

    total = 0
    for _ in range(trials):
        drawn = rng.sample(remaining, draw_n) if draw_n else []
        final = apply_hold_and_draw_from_sample(initial, hold_mask, drawn)
        cat = evaluate_hand(final).category
        total += paytable.payout_for(cat) * bet_per_hand

    return total / trials if trials else 0.0


def best_hold_mask_mc(
    initial: List[Card],
    paytable: PayTable,
    rng: random.Random,
    trials_per_mask: int = 200,
    bet_per_hand: int = 1,
) -> Tuple[int, float]:
    best_mask = 0
    best_ev = -1.0

    # Precompute dealt/remaining once per hand and pass through closure-ish pattern
    dealt = set(initial)
    remaining = [c for c in FULL_DECK if c not in dealt]

    for mask in range(32):
        # number of drawn cards depends only on mask
        held = ((mask & 0b00001) > 0) + ((mask & 0b00010) > 0) + ((mask & 0b00100) > 0) + ((mask & 0b01000) > 0) + ((mask & 0b10000) > 0)
        draw_n = 5 - held

        total = 0
        for _ in range(trials_per_mask):
            drawn = rng.sample(remaining, draw_n) if draw_n else []
            final = apply_hold_and_draw_from_sample(initial, mask, drawn)
            cat = evaluate_hand(final).category
            total += paytable.payout_for(cat) * bet_per_hand

        ev = total / trials_per_mask if trials_per_mask else 0.0
        if ev > best_ev:
            best_ev = ev
            best_mask = mask

    return best_mask, best_ev

