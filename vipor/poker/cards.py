from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

SUITS = ("S", "H", "D", "C")  # Spades, Hearts, Diamonds, Clubs
RANKS = tuple(range(2, 15))  # 2..14 (14 = Ace)


@dataclass(frozen=True, slots=True)
class Card:
    rank: int  # 2..14
    suit: str  # one of SUITS

    def __str__(self) -> str:
        r = {11: "J", 12: "Q", 13: "K", 14: "A"}.get(self.rank, str(self.rank))
        return f"{r}{self.suit}"


def cards_str(cards: Iterable[Card]) -> str:
    return " ".join(str(c) for c in cards)

