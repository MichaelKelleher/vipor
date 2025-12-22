from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

from .cards import Card

# Ranks: 2..14 where 11=J,12=Q,13=K,14=A
ROYAL_RANKS = {10, 11, 12, 13, 14}


# ----------------------------
# Mask helpers
# ----------------------------

def mask_from_indices(indices: Sequence[int]) -> int:
    """Build a 5-bit hold mask from card indices (0..4)."""
    mask = 0
    for i in indices:
        if i < 0 or i > 4:
            raise ValueError(f"card index out of range: {i}")
        mask |= 1 << i
    return mask


def indices_from_mask(mask: int) -> List[int]:
    """Return held card indices from a 5-bit hold mask."""
    return [i for i in range(5) if (mask & (1 << i))]


def mask_to_holds(mask: int) -> str:
    """Human-friendly mask: 'H-H--' means hold indices 0 and 2."""
    return "".join("H" if (mask & (1 << i)) else "-" for i in range(5))


# ----------------------------
# Simple selectors
# ----------------------------

def indices_of_rank(cards: Sequence[Card], rank: int) -> List[int]:
    return [i for i, c in enumerate(cards) if c.rank == rank]


def indices_of_suit(cards: Sequence[Card], suit: str) -> List[int]:
    return [i for i, c in enumerate(cards) if c.suit == suit]


def ranks(cards: Sequence[Card]) -> List[int]:
    return [c.rank for c in cards]


def suits(cards: Sequence[Card]) -> List[str]:
    return [c.suit for c in cards]


# ----------------------------
# Count helpers
# ----------------------------

def rank_counts(cards: Sequence[Card]) -> Counter:
    return Counter(c.rank for c in cards)


def suit_counts(cards: Sequence[Card]) -> Counter:
    return Counter(c.suit for c in cards)


def groups_by_rank(cards: Sequence[Card]) -> Dict[int, List[int]]:
    """rank -> indices"""
    out: Dict[int, List[int]] = {}
    for i, c in enumerate(cards):
        out.setdefault(c.rank, []).append(i)
    return out


def groups_by_suit(cards: Sequence[Card]) -> Dict[str, List[int]]:
    """suit -> indices"""
    out: Dict[str, List[int]] = {}
    for i, c in enumerate(cards):
        out.setdefault(c.suit, []).append(i)
    return out


# ----------------------------
# Pair / trips / quads
# ----------------------------

def pair_ranks(cards: Sequence[Card]) -> List[int]:
    """All pair ranks present (descending)."""
    counts = rank_counts(cards)
    return sorted([r for r, n in counts.items() if n == 2], reverse=True)


def trips_ranks(cards: Sequence[Card]) -> List[int]:
    """All trips ranks present (descending)."""
    counts = rank_counts(cards)
    return sorted([r for r, n in counts.items() if n == 3], reverse=True)

def quad_indices(cards: Sequence[Card]) -> Optional[List[int]]:
    """Return indices of the four-of-a-kind cards if present, else None."""
    counts = rank_counts(cards)
    for r, n in counts.items():
        if n == 4:
            return [i for i, c in enumerate(cards) if c.rank == r]
    return None

def quad_ranks(cards: Sequence[Card]) -> List[int]:
    """All quad ranks present (descending)."""
    counts = rank_counts(cards)
    return sorted([r for r, n in counts.items() if n == 4], reverse=True)


def best_pair_indices(cards: Sequence[Card]) -> Optional[List[int]]:
    """
    Best (highest) pair indices if any pair exists, else None.
    For two-pair hands, returns the higher pair.
    """
    pairs = pair_ranks(cards)
    if not pairs:
        return None
    target = pairs[0]
    return indices_of_rank(cards, target)


def job_pair_indices(cards: Sequence[Card]) -> Optional[List[int]]:
    """Indices of a Jacks-or-Better pair if present, else None."""
    pairs = pair_ranks(cards)
    for r in pairs:
        if r >= 11:
            return indices_of_rank(cards, r)
    return None


# ----------------------------
# Flush / Royal draw helpers
# ----------------------------

def n_to_flush(cards: Sequence[Card], n: int) -> Optional[List[int]]:
    """
    Return indices of cards in the best suit if you have at least n of that suit.
    If multiple suits tie, returns one deterministically (max suit count then suit).
    """
    if n <= 0:
        return []
    sc = suit_counts(cards)
    if not sc:
        return None
    suit, cnt = sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    if cnt >= n:
        return indices_of_suit(cards, suit)
    return None


def n_to_royal(cards: Sequence[Card], n: int) -> Optional[List[int]]:
    """
    Return indices of royal-ranked cards (T,J,Q,K,A) in a single suit if count >= n.
    Chooses the suit with the most royal cards; ties broken deterministically by suit.
    """
    if n <= 0:
        return []

    by_suit: Dict[str, List[int]] = {}
    for i, c in enumerate(cards):
        if c.rank in ROYAL_RANKS:
            by_suit.setdefault(c.suit, []).append(i)

    if not by_suit:
        return None

    # best = most indices; tie by suit string
    suit, idx = sorted(by_suit.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0]
    if len(idx) >= n:
        return idx
    return None


# ----------------------------
# Straight-ish draw helpers
# (These are intentionally conservative; use carefully.)
# ----------------------------

def unique_ranks_sorted(cards: Sequence[Card]) -> List[int]:
    return sorted(set(ranks(cards)))


def is_wheel_ranks(unique_sorted: Sequence[int]) -> bool:
    # A-2-3-4-5 unique ranks
    return list(unique_sorted) == [2, 3, 4, 5, 14]


def n_to_straight_unique_ranks(cards: Sequence[Card], n: int) -> Optional[List[int]]:
    """
    VERY simple helper: checks if the hand contains >=n cards that can fit in some 5-rank straight window.
    Returns indices for one such window, else None.

    Notes:
    - Ignores suit.
    - Treats A as high (14) and also supports wheel (A2345) via special case.
    - Does not handle all VP 'inside straight' nuances; it's a building block.
    """
    if n <= 0:
        return []

    # Map rank -> one index (first occurrence). Duplicates handled by choosing one representative.
    rank_to_index: Dict[int, int] = {}
    for i, c in enumerate(cards):
        rank_to_index.setdefault(c.rank, i)

    uniq = sorted(rank_to_index.keys())
    if len(uniq) < n:
        return None

    # Consider wheel straight explicitly
    wheel = [14, 2, 3, 4, 5]
    wheel_present = [r for r in wheel if r in rank_to_index]
    if len(wheel_present) >= n:
        return [rank_to_index[r] for r in wheel_present]

    # Consider all possible 5-rank windows from 2..10 start (10-J-Q-K-A ends at 14)
    for start in range(2, 11):
        window = list(range(start, start + 5))
        present = [r for r in window if r in rank_to_index]
        if len(present) >= n:
            return [rank_to_index[r] for r in present]

    return None

def four_to_outside_straight(cards: Sequence[Card]) -> Optional[List[int]]:
    """
    Return indices of a 4-card open-ended straight draw (outside straight),
    or None if only inside/gutshot or no straight draw exists.

    Examples that return indices:
      A-2-3-4  (needs 5)
      2-3-4-5  (needs A or 6)
      9-T-J-Q  (needs 8 or K)
      T-J-Q-K  (needs 9 or A)

    Examples that return None:
      2-3-4-6  (inside, needs 5)
      5-6-8-9  (inside, needs 7)
      A-3-4-5  (inside, needs 2)
    """

    # Map rank -> index (dedupe ranks; choose first index deterministically)
    rank_to_index: dict[int, int] = {}
    for i, c in enumerate(cards):
        rank_to_index.setdefault(c.rank, i)

    ranks = sorted(rank_to_index.keys())
    if len(ranks) < 4:
        return None

    # --- Wheel special case: A-2-3-4 ---
    wheel = {14, 2, 3, 4}
    if wheel.issubset(rank_to_index):
        return [rank_to_index[r] for r in sorted(wheel)]

    # --- General case: sliding 5-rank windows ---
    # Valid straight windows start at 2..10
    for start in range(2, 11):
        window = set(range(start, start + 5))
        present = window & set(ranks)

        if len(present) == 4:
            missing = window - present
            missing_rank = next(iter(missing))

            # Outside straight: missing rank must be at an end
            if missing_rank == start or missing_rank == start + 4:
                return [rank_to_index[r] for r in sorted(present)]

    return None

# ----------------------------
# High card helpers
# ----------------------------

def high_card_indices(cards: Sequence[Card], min_rank: int = 11) -> List[int]:
    """Indices of cards with rank >= min_rank (default J or higher)."""
    return [i for i, c in enumerate(cards) if c.rank >= min_rank]


def top_n_high_cards(cards: Sequence[Card], n: int, min_rank: int = 11) -> List[int]:
    """Indices of top-N high cards (rank desc), filtered by min_rank."""
    highs = [(i, c.rank) for i, c in enumerate(cards) if c.rank >= min_rank]
    highs.sort(key=lambda t: (-t[1], t[0]))
    return [i for i, _r in highs[:n]]


# ----------------------------
# Convenience: build a hold decision mask directly from predicates
# ----------------------------

def mask_where(cards: Sequence[Card], pred) -> int:
    """
    Build a mask holding all indices i where pred(cards[i]) is True.
    Example: mask_where(cards, lambda c: c.rank >= 11)
    """
    idx = [i for i, c in enumerate(cards) if pred(c)]
    return mask_from_indices(idx)

