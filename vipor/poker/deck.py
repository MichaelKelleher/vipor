from __future__ import annotations

import random
from typing import List, Optional

from .cards import Card


class Deck:
    def __init__(
        self,
        cards: Optional[List[Card]] = None,
        rng: Optional[random.Random] = None,
    ):
        self.rng = rng or random.Random()
        self._initial_cards = list(cards) if cards is not None else None
        self.cards: List[Card] = []
        self.reset()

    def _fresh_52(self) -> List[Card]:
        return [
            Card(rank, suit)
            for suit in ("C", "D", "H", "S")
            for rank in range(2, 15)
        ]

    def reset(self) -> None:
        """
        Reset deck back to its initial composition, then shuffle.
        - If initialized with cards=[...], resets to those cards.
        - Else resets to a fresh 52-card deck.
        """
        if self._initial_cards is not None:
            self.cards = list(self._initial_cards)
        else:
            self.cards = self._fresh_52()
        self.shuffle()

    def shuffle(self) -> None:
        self.rng.shuffle(self.cards)

    def deal(self, n: int) -> List[Card]:
        if n > len(self.cards):
            raise ValueError("Not enough cards left to deal")
        out = self.cards[:n]
        del self.cards[:n]
        return out

    def draw(self) -> Card:
        if not self.cards:
            raise ValueError("No cards left to draw")
        return self.cards.pop(0)

