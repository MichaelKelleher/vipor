from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Callable, Dict

from .cards import Card
from .hold import HoldDecision
from .hot_roll import HotRollConfig, expected_multiplier_2d6



@dataclass(frozen=True)
class McBestConfig:
    trials: int = 200
    seed: int = 42


def _fresh_deck_excluding(cards: list[Card]) -> list[Card]:
    excluded = {(c.rank, c.suit) for c in cards}
    deck: list[Card] = []
    for suit in ("C", "D", "H", "S"):
        for rank in range(2, 15):
            if (rank, suit) not in excluded:
                deck.append(Card(rank=rank, suit=suit))
    if len(deck) != 47:
        raise ValueError(f"Expected 47 remaining cards, got {len(deck)}")
    return deck

def _draw_k(rng: random.Random, remaining: list[Card], k: int) -> tuple[Card, ...]:
    """Fast draw without replacement. Optimized for small k (<=3)."""
    n = len(remaining)
    if k <= 0:
        return ()
    if k == 1:
        return (remaining[rng.randrange(n)],)
    if k == 2:
        i = rng.randrange(n)
        j = rng.randrange(n - 1)
        if j >= i:
            j += 1
        return (remaining[i], remaining[j])
    if k == 3:
        i = rng.randrange(n)
        j = rng.randrange(n - 1)
        if j >= i:
            j += 1
        while True:
            kidx = rng.randrange(n)
            if kidx != i and kidx != j:
                break
        return (remaining[i], remaining[j], remaining[kidx])
    # fallback (k 4-5 happens when holding 1 or 0 cards)
    return tuple(rng.sample(remaining, k))

def _mc_ev_for_mask(
    *,
    paytable,
    evaluator: Callable[[list[Card]], object],
    init: list[Card],
    mask: int,
    trials: int,
    rng: random.Random,
    remaining_deck: list[Card],
    expected_mult: float,
    paytable_bet: int,
) -> float:
    # Precompute which positions we will draw into (avoid "i in hold_idx" cost)
    draw_pos: list[int] = []
    for i in range(5):
        if not (mask & (1 << i)):
            draw_pos.append(i)
    draw_n = len(draw_pos)

    # Reuse one buffer instead of copying init[:] every trial
    final = init[:]  # copy once; we only overwrite draw positions

    total_pay = 0.0
    for _ in range(trials):
        if draw_n:
            drawn = _draw_k(rng, remaining_deck, draw_n)
            for di, pos in enumerate(draw_pos):
                final[pos] = drawn[di]

        ev = evaluator(final)
        unit = paytable.payout_for(ev.category)  # per-coin payout
        total_pay += (unit * paytable_bet) * expected_mult

    return total_pay / trials if trials else 0.0


def make_mc_best_strategy(
    paytable,
    evaluator: Callable[[list[Card]], object],
    trials: int = 200,
    seed: int = 42,
    *,
    hot_roll_cfg: HotRollConfig | None = None,
    hot_roll_paytable_bet: int = 5,
) -> Callable[[list[Card]], HoldDecision]:

    
    cfg = McBestConfig(trials=trials, seed=seed)

    cache: Dict[tuple[tuple[int, str], ...], HoldDecision] = {}

    if hot_roll_cfg is not None:
        expected_mult = expected_multiplier_2d6(hot_roll_cfg.p_per_hand)
        paytable_bet = hot_roll_paytable_bet  # typically 5
    else:
        expected_mult = 1.0
        paytable_bet = 1


    def strategy(init: list[Card]) -> HoldDecision:
        key = tuple((c.rank, c.suit) for c in init)
        if key in cache:
            return cache[key]

        rng = random.Random(cfg.seed ^ (hash(key) & 0xFFFFFFFF))
        remaining = _fresh_deck_excluding(init)

        best_mask = 0
        best_ev = -1.0
        for mask in range(32):
            ev = _mc_ev_for_mask(
                paytable=paytable,
                evaluator=evaluator,
                init=init,
                mask=mask,
                trials=cfg.trials,
                rng=rng,
                remaining_deck=remaining,
                expected_mult=expected_mult,
                paytable_bet=paytable_bet,
            )

            if ev > best_ev:
                best_ev = ev
                best_mask = mask

        d = HoldDecision(mask=best_mask)
        cache[key] = d
        return d

    return strategy

