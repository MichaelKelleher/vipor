# vipor/poker/strategy_rules_j_riff.py
from __future__ import annotations

from typing import Dict, List

from .cards import Card
from .hold import HoldDecision
from .strategy_helpers import ROYAL_RANKS, mask_from_indices

DEUCE_RANK = 2
ACE_RANK = 14

ROYAL_SET = {10, 11, 12, 13, 14}  # T,J,Q,K,A



def _idxs(cards: List[Card], pred) -> List[int]:
    return [i for i, c in enumerate(cards) if pred(c)]


def _choose_evaluator():
    """
    Prefer the Deuces Wild Bonus evaluator if present.
    Fall back to the JoB evaluator.
    """
    try:
        from .hand_eval_deuces_bonus import evaluate_deuces_bonus
        return evaluate_deuces_bonus
    except Exception:
        from .hand_eval import evaluate_hand
        return evaluate_hand


# Keep this conservative & string-based to avoid fragile imports of constants.
# Add categories here as your evaluator defines them.
MADE_HAND_CATEGORIES = {
    "royal_flush",
    "natural_royal_flush",
    "wild_royal_flush",
    "straight_flush",
    "five_of_a_kind",
    "five_aces",
    "five_345",
    "five_6_to_k",
    "four_of_a_kind",
    "four_deuces",
    "four_deuces_with_ace",
    "full_house",
    "flush",
    "straight",
}

def j_riff_strategy_deuces_wild_bonus(cards: List[Card]) -> HoldDecision:
    """
    j_riff strategy for Deuces Wild Bonus (rule-driven, intentionally simple).

    Rules (per your spec):
      - Always keep deuces.
      - Keep Royal Flush; keep made hands.
      - 4 deuces: keep 4 deuces; keep Ace kicker only (throw non-ace kicker).
      - 3 deuces: keep 3 deuces only (ignore royals).
      - 2 deuces + two royals: keep those; but 2 deuces + single royal => throw royal (keep only deuces).
      - Keep a single pair of 3/4/5; never keep two pair.
    """
    deuce_idx = _idxs(cards, lambda c: c.rank == DEUCE_RANK)
    d = len(deuce_idx)

    evaluator = _choose_evaluator()

    # --- Keep made hands (including Royal Flush)
    # (We do this before the "throw kicker" rules except for the explicit 4-deuce kicker rule below.)
    try:
        cat = evaluator(cards).category
    except Exception:
        cat = None

    # --- 4 deuces special-case: throw non-ace kicker (even though it's technically "made")
    if d == 4:
        ace_idx = _idxs(cards, lambda c: c.rank == ACE_RANK)
        hold = deuce_idx + ace_idx  # ace_idx is either [] or [kicker_index]
        return HoldDecision(mask_from_indices(hold))

    # --- Always keep deuces (with your specific sub-rules)
    if d == 3:
        # keep 3 deuces only; ignore any royal kicker(s)
        return HoldDecision(mask_from_indices(deuce_idx))

    if d == 2:
        # Keep 2 deuces + 2+ royals ONLY if the royals are suited (aiming at wild royal / straight flush).
        royal_idx = _idxs(cards, lambda c: (c.rank in ROYAL_RANKS) and (c.rank != DEUCE_RANK))

        if len(royal_idx) >= 3:
            royals_by_suit: Dict[str, List[int]] = {}
            for i in royal_idx:
                royals_by_suit.setdefault(cards[i].suit, []).append(i)

            # Find the suit with the most royal cards
            best_suit = max(royals_by_suit, key=lambda s: len(royals_by_suit[s]))
            suited_royals = royals_by_suit[best_suit]

            if len(suited_royals) >= 2:
                hold = deuce_idx + suited_royals
                return HoldDecision(mask_from_indices(hold))

        # Otherwise: keep only deuces
        return HoldDecision(mask_from_indices(deuce_idx))


    if d == 1:
        # J's spec:
        # - with one deuce, keep MADE HANDS
        # - except if it's a straight, keep only the deuce
        if isinstance(cat, str):
            cat_l = cat.lower()
            if cat_l == "straight":
                return HoldDecision(mask_from_indices(deuce_idx))
            #SUBOPTIMAL
            if cat_l == "flush":
                return HoldDecision(mask_from_indices(deuce_idx))
            if cat_l in MADE_HAND_CATEGORIES:
                return HoldDecision(mask=31)

        # With 1 deuce, any natural pair becomes (at least) trips.
        counts: Dict[int, List[int]] = {}

        for i, c in enumerate(cards):
            if c.rank == DEUCE_RANK:
                continue
            counts.setdefault(c.rank, []).append(i)

        pair_idxs = [idxs for idxs in counts.values() if len(idxs) == 2]

        if len(pair_idxs) == 1:
            hold = deuce_idx + pair_idxs[0]
            return HoldDecision(mask_from_indices(hold))

        # Otherwise: still follow "always keep a deuce"
        return HoldDecision(mask_from_indices(deuce_idx))

    # For everything else: if it's a made hand, keep it.
    # (If your evaluator uses different names, add them to MADE_HAND_CATEGORIES above.)
    royal_idx = _idxs(cards, lambda c: (c.rank in ROYAL_RANKS) and (c.rank != DEUCE_RANK))

#   SUBOPTIMAL
    if len(royal_idx) >= 3:
#        print("Royals Check: ", len(royal_idx))
        royals_by_suit: Dict[str, List[int]] = {}
        for i in royal_idx:
            royals_by_suit.setdefault(cards[i].suit, []).append(i)
        # Find the suit with the most royal cards
        best_suit = max(royals_by_suit, key=lambda s: len(royals_by_suit[s]))
        suited_royals = royals_by_suit[best_suit]

        if len(suited_royals) >= 2:
            hold = deuce_idx + suited_royals
            return HoldDecision(mask_from_indices(hold))


    if isinstance(cat, str) and cat.lower() in MADE_HAND_CATEGORIES:
        return HoldDecision(mask=31)


    # --- No deuces: if any pair exists, keep EXACTLY ONE pair.
    # Preference order:
    #   1) AA always
    #   2) lowest pair in 3–5
    #   3) lowest pair in 6–K
    counts: Dict[int, List[int]] = {}
    for i, c in enumerate(cards):
        counts.setdefault(c.rank, []).append(i)

    trip_ranks = sorted([r for r, idxs in counts.items() if len(idxs) == 3])
    if trip_ranks:
        if ACE_RANK in trip_ranks:
            return HoldDecision(mask_from_indices(counts[ACE_RANK]))
        low_35 = [r for r in trip_ranks if 3 <= r <= 5]
        if low_35:
            keep_rank = min(low_35)
            return HoldDecision(mask_from_indices(counts[keep_rank]))
        mid_6k = [r for r in trip_ranks if 6 <= r <= 13]
        if mid_6k:
            keep_rank = min(mid_6k)
            return HoldDecision(mask_from_indices(counts[keep_rank]))

    # --- No deuces special: 3-to-a-royal (suited) beats pairs (per J spec/tests)
    if d == 0:
        by_suit: Dict[str, List[int]] = {"C": [], "D": [], "H": [], "S": []}
        for i, c in enumerate(cards):
            if c.rank in ROYAL_SET:
                by_suit[c.suit].append(i)

        # pick the suit with the most royal cards
        best = max(by_suit.values(), key=len) if by_suit else []
        if len(best) >= 3:
            # hold just those royal cards in that suit
            return HoldDecision(mask_from_indices(best))

    pair_ranks = sorted([r for r, idxs in counts.items() if len(idxs) == 2])

    if not pair_ranks:
        return HoldDecision(mask=0)

    # 1) Always keep aces if paired
    if ACE_RANK in pair_ranks:
        return HoldDecision(mask_from_indices(counts[ACE_RANK]))

    # 2) Prefer low pairs 3–5 (choose the lowest if multiple)
    low_35 = [r for r in pair_ranks if 3 <= r <= 5]
    if low_35:
        keep_rank = min(low_35)
        return HoldDecision(mask_from_indices(counts[keep_rank]))

    # 3) Otherwise keep the lowest pair in 6–K (6..13)
    mid_6k = [r for r in pair_ranks if 6 <= r <= 13]
    if mid_6k:
        keep_rank = min(mid_6k)
        return HoldDecision(mask_from_indices(counts[keep_rank]))

    # Fallback: keep the lowest pair rank we found
    return HoldDecision(mask_from_indices(counts[min(pair_ranks)]))

