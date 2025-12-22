from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .cards import Card

# Deuces Wild Bonus categories (IGT-style; paytable decides exact payouts)
NATURAL_ROYAL_FLUSH = "natural_royal_flush"
FOUR_DEUCES_WITH_ACE = "four_deuces_with_ace"
FOUR_DEUCES = "four_deuces"
WILD_ROYAL_FLUSH = "wild_royal_flush"
FIVE_ACES = "five_aces"
FIVE_345 = "five_345"
FIVE_6_TO_K = "five_6_to_k"
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
STRAIGHT_SEQS: List[Tuple[int, int, int, int, int]] = [
    (14, 2, 3, 4, 5),  # wheel (A2345)
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
    natural_ranks = {c.rank for c in naturals}
    present = sum(1 for r in seq if r in natural_ranks)
    missing = 5 - present
    return missing <= wilds


def _can_make_any_straight(naturals: Sequence[Card], wilds: int) -> bool:
    return any(_can_make_sequence(naturals, wilds, seq) for seq in STRAIGHT_SEQS)


def _can_make_royal(naturals: Sequence[Card], wilds: int) -> bool:
    return _can_make_sequence(naturals, wilds, ROYAL_SEQ)


def _can_make_n_of_kind(rc: Dict[int, int], wilds: int, n: int) -> bool:
    # Any existing rank can be boosted by wilds
    for _r, cnt in rc.items():
        if cnt + wilds >= n:
            return True
    # Or created purely from wilds (e.g., 3 deuces = trips)
    return wilds >= n


def _can_make_full_house(rc: Dict[int, int], wilds: int) -> bool:
    """
    Small brute-force: can we allocate wilds to form a 3-of-kind + 2-of-kind?
    Candidates are natural ranks plus a reasonable rank universe (3..14 excluding 2).
    """
    candidates = set(rc.keys()) | {3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}

    for r3 in candidates:
        c3 = rc.get(r3, 0)
        need3 = max(0, 3 - c3)
        if need3 > wilds:
            continue
        w_left = wilds - need3

        for r2 in candidates:
            if r2 == r3:
                continue
            c2 = rc.get(r2, 0)
            need2 = max(0, 2 - c2)
            if need2 <= w_left:
                return True

    return False


def _is_natural_royal_flush(naturals: Sequence[Card], wilds: int) -> bool:
    if wilds != 0:
        return False
    if len(naturals) != 5:
        return False
    if not _all_naturals_same_suit(naturals):
        return False
    ranks = sorted({c.rank for c in naturals})
    return tuple(ranks) == ROYAL_SEQ


def _four_deuces_category(cards: Sequence[Card], wilds: int) -> str | None:
    if wilds != 4:
        return None
    # Exactly one natural remains; kicker matters in this bonus variant
    natural = next((c for c in cards if c.rank != 2), None)
    if natural and natural.rank == 14:
        return FOUR_DEUCES_WITH_ACE
    return FOUR_DEUCES


def _five_kind_category(rc: Dict[int, int], wilds: int) -> str | None:
    """
    Deuces Wild Bonus splits 5-of-a-kind payouts:
      - five_aces
      - five_345
      - five_6_to_k

    We return the best *payout class* available.
    Requires wilds > 0 in DW.
    """
    if wilds <= 0:
        return None

    # Prefer in payout order: A > 3/4/5 > 6..K
    if rc.get(14, 0) + wilds >= 5:
        return FIVE_ACES

    for r in (3, 4, 5):
        if rc.get(r, 0) + wilds >= 5:
            return FIVE_345

    for r in range(6, 14):  # 6..13 (K)
        if rc.get(r, 0) + wilds >= 5:
            return FIVE_6_TO_K

    # If no naturals at all, wilds alone can form five-of-a-kind of any rank.
    # With <=4 wilds, you still need at least one natural to reach 5 cards total,
    # so this generally won't trigger; keep it as a safe fallback.
    if not rc and wilds >= 5:
        return FIVE_ACES

    return None


def evaluate_deuces_bonus(cards: Sequence[Card]) -> EvalResult:
    """
    Deuces Wild Bonus evaluator (IGT-style category granularity).

    Ranking order (matches common DW Bonus paytables):
      natural_royal_flush
      four_deuces_with_ace
      four_deuces
      wild_royal_flush
      five_aces
      five_345
      five_6_to_k
      straight_flush
      four_of_a_kind
      full_house
      flush
      straight
      three_of_a_kind
      nothing
    """
    if len(cards) != 5:
        raise ValueError("evaluate_deuces_bonus expects exactly 5 cards")

    wilds = _count_deuces(cards)
    naturals = _naturals(cards)
    rc = _rank_counts(naturals)

    # --- Top hands ---
    if _is_natural_royal_flush(naturals, wilds):
        return EvalResult(NATURAL_ROYAL_FLUSH)

    four_deuces_cat = _four_deuces_category(cards, wilds)
    if four_deuces_cat:
        return EvalResult(four_deuces_cat)

    # Wild royal flush (royal w/ >=1 deuce; suited naturals; ranks can be completed by wilds)
    if wilds > 0 and _all_naturals_same_suit(naturals) and _can_make_royal(naturals, wilds):
        return EvalResult(WILD_ROYAL_FLUSH)

    five_cat = _five_kind_category(rc, wilds)
    if five_cat:
        return EvalResult(five_cat)

    # Straight flush (including wheel), if naturals can be made into a straight and all suited
    if _all_naturals_same_suit(naturals) and _can_make_any_straight(naturals, wilds):
        return EvalResult(STRAIGHT_FLUSH)

    # Four of a kind (any rank, including via wilds)
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

