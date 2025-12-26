from collections import Counter
from dataclasses import dataclass
from typing import List

from .cards import Card

ROYAL_FLUSH = "royal_flush"
STRAIGHT_FLUSH = "straight_flush"
FOUR_ACES_234 = "four_aces_234"
FOUR_LOW_ACE = "four_low_ace"
FOUR_ACES = "four_aces"
FOUR_234 = "four_234"
FOUR = "four_of_a_kind"
FULL_HOUSE = "full_house"
FLUSH = "flush"
STRAIGHT = "straight"
THREE = "three_of_a_kind"
TWO_PAIR = "two_pair"
JOB = "jacks_or_better"
NOTHING = "nothing"


@dataclass(frozen=True)
class HandResult:
    category: str


def _is_straight(unique_sorted: List[int]) -> bool:
    # Requires 5 unique ranks
    if len(unique_sorted) != 5:
        return False
    # Wheel: A-2-3-4-5
    if unique_sorted == [2, 3, 4, 5, 14]:
        return True
    start = unique_sorted[0]
    return unique_sorted == list(range(start, start + 5))


def evaluate_hand(cards: List[Card]) -> HandResult:
    if len(cards) != 5:
        raise ValueError("evaluate_hand expects exactly 5 cards")

    ranks = sorted(c.rank for c in cards)
    counts = Counter(ranks)
    shape = sorted(counts.values(), reverse=True)
    unique = sorted(counts.keys())

    flush = len({c.suit for c in cards}) == 1
    straight = _is_straight(unique)

    if flush and straight:
        if set(unique) == {10, 11, 12, 13, 14}:
            return HandResult(ROYAL_FLUSH)
        return HandResult(STRAIGHT_FLUSH)

    if shape == [4, 1]:
        quad_rank = next(r for r, c in counts.items() if c == 4)
        kicker_rank = next(r for r, c in counts.items() if c == 1)

        if quad_rank == 14:
            # Aces
            if kicker_rank in (2, 3, 4):
                return HandResult(FOUR_ACES_234)
            return HandResult(FOUR_ACES)

        if quad_rank in (2, 3, 4):
            # 2–4 quads
            if kicker_rank in (14, 2, 3, 4):
                return HandResult(FOUR_LOW_ACE)
            return HandResult(FOUR_234)

        # 5–K quads
        return HandResult(FOUR)

    if shape == [3, 2]:
        return HandResult(FULL_HOUSE)
    if flush:
        return HandResult(FLUSH)
    if straight:
        return HandResult(STRAIGHT)

    if shape == [3, 1, 1]:
        return HandResult(THREE)
    if shape == [2, 2, 1]:
        return HandResult(TWO_PAIR)
    if shape == [2, 1, 1, 1]:
        pair_rank = max(r for r, c in counts.items() if c == 2)
        return HandResult(JOB if pair_rank >= 11 else NOTHING)

    return HandResult(NOTHING)

