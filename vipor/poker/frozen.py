from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .cards import Card, RANKS, SUITS
from .hand_eval import evaluate_hand
from .paytable import PayTable

FULL_DECK: List[Card] = [Card(rank=r, suit=s) for s in SUITS for r in RANKS]


def parse_card(tok: str) -> Card:
    """
    Token format like: AS, KD, 10H, JC, 2S
    Suits: S,H,D,C
    Ranks: 2-10,J,Q,K,A
    """
    tok = tok.strip().upper()
    suit = tok[-1]
    r = tok[:-1]
    if suit not in {"S", "H", "D", "C"}:
        raise ValueError(f"Bad suit in {tok}")

    if r == "A":
        rank = 14
    elif r == "K":
        rank = 13
    elif r == "Q":
        rank = 12
    elif r == "J":
        rank = 11
    else:
        rank = int(r)

    if rank < 2 or rank > 14:
        raise ValueError(f"Bad rank in {tok}")
    return Card(rank=rank, suit=suit)


def parse_hand(s: str) -> List[Card]:
    parts = s.replace(",", " ").split()
    if len(parts) != 5:
        raise ValueError("Hand must have exactly 5 cards")
    cards = [parse_card(p) for p in parts]
    if len(set(cards)) != 5:
        raise ValueError("Hand has duplicates")
    return cards


@dataclass
class FrozenResult:
    trials: int
    hold_mask: int
    avg_payout: float
    avg_net: float
    category_counts: Dict[str, int]


def frozen_ev_mc(
    paytable: PayTable,
    initial: List[Card],
    hold_mask: int,
    trials: int,
    bet_per_hand: int = 1,
    seed: int = 1,
) -> FrozenResult:
    rng = random.Random(seed)

    dealt = set(initial)
    remaining = [c for c in FULL_DECK if c not in dealt]

    draw_positions = [i for i in range(5) if not (hold_mask & (1 << i))]
    draw_n = len(draw_positions)

    total_payout = 0
    cat_counts: Dict[str, int] = {}

    for _ in range(trials):
        drawn = rng.sample(remaining, draw_n) if draw_n else []
        final = initial[:]
        for pos, new_card in zip(draw_positions, drawn):
            final[pos] = new_card

        cat = evaluate_hand(final).category
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        total_payout += paytable.payout_for(cat) * bet_per_hand

    avg_payout = total_payout / trials if trials else 0.0
    avg_net = avg_payout - bet_per_hand

    return FrozenResult(
        trials=trials,
        hold_mask=hold_mask,
        avg_payout=avg_payout,
        avg_net=avg_net,
        category_counts=cat_counts,
    )

