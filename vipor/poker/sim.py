from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .cards import Card
from .deck import Deck
from .paytable import PayTable
from .strategy import HoldDecision, hold_any_pair_else_none
from .hand_eval import evaluate_hand as default_evaluate_hand


@dataclass
class SimResult:
    hands: int
    total_bet: int
    total_payout: int
    total_net: int
    ev_per_hand: float
    return_pct: float
    category_counts: Dict[str, int]


def simulate(
    paytable: PayTable,
    hands: int,
    bet_per_hand: int = 1,
    seed: int = 42,
    trace_n: int = 0,
    strategy_fn: Callable[[List[Card]], HoldDecision] = hold_any_pair_else_none,
    evaluator: Callable[[List[Card]], object] = default_evaluate_hand,
) -> SimResult:
    rng = random.Random(seed)
    deck = Deck(rng=rng)

    total_bet = hands * bet_per_hand
    total_payout = 0
    category_counts: Dict[str, int] = {}

    for h in range(hands):
        deck.reset()
        init = deck.deal(5)

        decision = strategy_fn(init)
        mask = decision.mask

        final = init[:]
        for i in range(5):
            if not (mask & (1 << i)):
                final[i] = deck.draw()

        # evaluator returns either EvalResult(category=...) or something with .category
        ev = evaluator(final)
        cat = ev.category  # both JoB and Deuces evaluators use this

        category_counts[cat] = category_counts.get(cat, 0) + 1
        total_payout += paytable.payout_for(cat) * bet_per_hand

        if h < trace_n:
            # Optional: keep your existing trace format if you like
            pass

    total_net = total_payout - total_bet
    ev_per_hand = total_net / hands if hands else 0.0
    return_pct = total_payout / total_bet if total_bet else 0.0

    return SimResult(
        hands=hands,
        total_bet=total_bet,
        total_payout=total_payout,
        total_net=total_net,
        ev_per_hand=ev_per_hand,
        return_pct=return_pct,
        category_counts=category_counts,
    )

