from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .cards import Card

# Deuces Wild categories (common set; paytables may vary)
NATURAL_ROYAL_FLUSH = "natural_royal_flush"
FOUR_DEUCES = "four_deuces"
WILD_ROYAL_FLUSH = "wild_royal_flush"
FIVE_OF_A_KIND = "five_of_a_kind"
STRAIGHT_FLUSH = "straight_flush"
FOUR_OF_A_KIND = "four_of_a_kind"
FULL_HOUSE = "full_house"
FLUSH = "flush"
STRAIGHT = "straight"
THREE_OF_A_KIND = "three_of_a_kind"
NOTHING = "nothing"


@dataclass(frozen=True)
class EvalResult:
    category: str


ROYAL_SEQ = (10, 11, 12, 13, 14)  # T J Q K A
# All possible 5-card straight sequences (Ace-low included)
STRAIGHT_SEQS: List[Tuple[int, int, int, int, int]] = [
    (14, 2, 3, 4, 5),  # wheel
    (2, 3, 4, 5, 6),
    (3, 4, 5, 6, 7),
    (4, 5, 6, 7, 8),
    (5, 6, 7, 8, 9),
    (6, 7, 8, 9, 10),
    (7, 8, 9, 10, 11),
    (8, 9, 10, 11, 12),
    (9, 10, 11, 12, 13),
    (10, 11, 12, 13, 14),
]


def _count_deuces(cards: Sequence[Card]) -> int:
    return sum(1 for c in cards if c.rank == 2)


def _naturals(cards: Sequence[Card]) -> List[Card]:
    return [c for c in cards if c.rank != 2]


def _rank_counts(naturals: Sequence[Card]) -> Dict[int, int]:
    d: Dict[int, int] = {}
    for c in naturals:
        d[c.rank] = d.get(c.rank, 0) + 1
    return d


def _all_naturals_same_suit(naturals: Sequence[Card]) -> bool:
    if not naturals:
        return True  # all wilds can choose a suit
    s = naturals[0].suit
    return all(c.suit == s for c in naturals)


def _can_make_sequence(naturals: Sequence[Card], wilds: int, seq: Tuple[int, ...]) -> bool:
    """Can we realize this exact 5-rank straight seq with given naturals + wilds?"""
    natural_ranks = {c.rank for c in naturals}
    present = sum(1 for r in seq if r in natural_ranks)
    missing = 5 - present
    return missing <= wilds


def _can_make_any_straight(naturals: Sequence[Card], wilds: int) -> bool:
    return any(_can_make_sequence(naturals, wilds, seq) for seq in STRAIGHT_SEQS)


def _can_make_royal(naturals: Sequence[Card], wilds: int) -> bool:
    return _can_make_sequence(naturals, wilds, ROYAL_SEQ)


def _can_make_five_kind(rank_counts: Dict[int, int], wilds: int) -> bool:
    # Need some rank r where count[r] + wilds == 5 (since only 5 cards total)
    # If no naturals, wilds==5 can't happen in DW (only 4 deuces exist), but handle gracefully.
    if wilds == 5:
        return True
    for r, cnt in rank_counts.items():
        if cnt + wilds >= 5:
            return True
    return False


def _can_make_n_of_kind(rank_counts: Dict[int, int], wilds: int, n: int) -> bool:
    for _r, cnt in rank_counts.items():
        if cnt + wilds >= n:
            return True
    # also possible to make n-of-kind out of thin air if wilds >= n
    return wilds >= n


def _can_make_full_house(rank_counts: Dict[int, int], wilds: int) -> bool:
    """
    Determine if we can make a full house (3+2) with rank counts + wilds.
    Brute-force small search over plausible ranks.
    """
    # Candidate ranks: any existing natural ranks, plus a few "virtual" ranks (3..14 excluding deuce=2)
    candidates = set(rank_counts.keys()) | {3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}

    for r3 in candidates:
        c3 = rank_counts.get(r3, 0)
        need3 = max(0, 3 - c3)
        if need3 > wilds:
            continue
        w2 = wilds - need3

        for r2 in candidates:
            if r2 == r3:
                continue
            c2 = rank_counts.get(r2, 0)
            need2 = max(0, 2 - c2)
            if need2 <= w2:
                return True

    return False


def evaluate_deuces(cards: Sequence[Card]) -> EvalResult:
    """
    Deuces Wild evaluator (no kickers, no joker).

    Ranking order used (typical DW paytables):
      natural_royal_flush
      four_deuces
      wild_royal_flush
      five_of_a_kind
      straight_flush
      four_of_a_kind
      full_house
      flush
      straight
      three_of_a_kind
      nothing
    """
    if len(cards) != 5:
        raise ValueError("evaluate_deuces expects exactly 5 cards")

    wilds = _count_deuces(cards)
    naturals = _naturals(cards)
    rc = _rank_counts(naturals)

    # ---- Top hands ----
    # Natural royal flush: no wilds AND already a royal flush
    # (We detect this as: all 5 are naturals, same suit, ranks are exactly royal set)
    if wilds == 0 and _all_naturals_same_suit(naturals):
        nr = sorted({c.rank for c in naturals})
        if tuple(nr) == ROYAL_SEQ:
            return EvalResult(NATURAL_ROYAL_FLUSH)

    # Four deuces: exactly 4 wilds (all deuces)
    if wilds == 4:
        return EvalResult(FOUR_DEUCES)

    # Wild royal flush: can make royal AND can make flush suit with naturals
    if wilds > 0 and _all_naturals_same_suit(naturals) and _can_make_royal(naturals, wilds):
        return EvalResult(WILD_ROYAL_FLUSH)

    # Five of a kind
    if wilds > 0 and _can_make_five_kind(rc, wilds):
        return EvalResult(FIVE_OF_A_KIND)

    # Straight flush
    if _all_naturals_same_suit(naturals) and _can_make_any_straight(naturals, wilds):
        return EvalResult(STRAIGHT_FLUSH)

    # Four of a kind
    if _can_make_n_of_kind(rc, wilds, 4):
        return EvalResult(FOUR_OF_A_KIND)

    # Full house
    if _can_make_full_house(rc, wilds):
        return EvalResult(FULL_HOUSE)

    # Flush
    if _all_naturals_same_suit(naturals):
        return EvalResult(FLUSH)

    # Straight
    if _can_make_any_straight(naturals, wilds):
        return EvalResult(STRAIGHT)

    # Three of a kind
    if _can_make_n_of_kind(rc, wilds, 3):
        return EvalResult(THREE_OF_A_KIND)

    return EvalResult(NOTHING)

