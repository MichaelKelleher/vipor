from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from .cards import Card, SUITS, RANKS


@dataclass
class Deck:
    rng: random.Random
    cards: List[Card]

    @classmethod
    def fresh(cls, rng: random.Random) -> "Deck":
        cards = [Card(rank=r, suit=s) for s in SUITS for r in RANKS]
        rng.shuffle(cards)
        return cls(rng=rng, cards=cards)

    def draw(self, n: int) -> List[Card]:
        if n < 0 or n > len(self.cards):
            raise ValueError("Cannot draw that many cards.")
        out = self.cards[:n]
        del self.cards[:n]
        return out

