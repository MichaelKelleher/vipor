#!/usr/bin/env python3
"""
holding_strategy_check.py

A tiny deterministic harness to sanity-check a strategy against a curated set
of "known-expected" hands. This is NOT EV testing; it's rule/regression testing.

Run:
  python -m vipor.poker.holding_strategy_check
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from vipor.poker.cards import Card
from vipor.poker.strategy_rules_j_riff import j_riff_strategy_deuces_wild_bonus


# --------- helpers ---------

RANK_MAP = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}
SUITS = {"C", "D", "H", "S"}

def parse_card(tok: str) -> Card:
    tok = tok.strip().upper()
    if len(tok) != 2:
        raise ValueError(f"Bad card token: {tok!r} (expected like 'AS' or '2D')")
    r, s = tok[0], tok[1]
    if r not in RANK_MAP or s not in SUITS:
        raise ValueError(f"Bad card token: {tok!r}")
    return Card(rank=RANK_MAP[r], suit=s)

def parse_hand(hand: str) -> List[Card]:
    toks = [t for t in hand.strip().split() if t]
    if len(toks) != 5:
        raise ValueError(f"Bad hand: {hand!r} (need 5 cards)")
    return [parse_card(t) for t in toks]

def mask_to_idxs(mask: int) -> List[int]:
    return [i for i in range(5) if (mask & (1 << i))]

def idxs_to_mask(idxs: List[int]) -> int:
    m = 0
    for i in idxs:
        m |= (1 << i)
    return m

def mask_to_str(mask: int) -> str:
    # e.g. 0b00101 -> "H-H--" (index 0 is leftmost)
    return "".join("H" if (mask & (1 << i)) else "-" for i in range(5))


# --------- test cases ---------

@dataclass(frozen=True)
class Case:
    hand: str
    expected_idxs: List[int]
    note: str = ""

CASES: List[Case] = [
    # --- 4 deuces (keep 4; keep Ace kicker only)
    Case("2C 2D 2H 2S AD", [0, 1, 2, 3, 4], "4 deuces + Ace => hold all (ace kicker)"),
    Case("2C 2D 2H 2S KD", [0, 1, 2, 3], "4 deuces + non-ace => hold only deuces"),

    # --- 3 deuces (keep deuces only)
    Case("2C 2D 2H AS KS", [0, 1, 2], "3 deuces => deuces only"),
    Case("2C 2D 2H TD JD", [0, 1, 2], "3 deuces + royal-ish => still deuces only"),

    # --- 2 deuces
    Case("2D 2S TD JD 9D", [0, 1, 2, 3], "2 deuces + suited TJ (D) => hold deuces + suited royals"),
    Case("2D 2S JD QH 8S", [0, 1], "2 deuces + off-suit JQ => hold deuces only (your recent bug)"),
    Case("2H 2S AH KH 7D", [0, 1, 2, 3], "2 deuces + suited AK (H) => hold deuces + suited royals"),
    Case("2H 2S AH KD 7D", [0, 1], "2 deuces + off-suit AK => hold deuces only"),

    # --- 1 deuce (your current intended rule-set)
    # If you implement: "d==1 keep made hands EXCEPT straight => keep only the deuce",
    # these are the kind of cases you want:
    Case("2D JD QD KD AD", [0, 1, 2, 3, 4], "1 deuce + TJQKA suited => wild royal flush (made) => hold all"),
    Case("2C 3D 4H 5S 6C", [0], "1 deuce + straight-ish => keep deuce only (if straight exception)"),

    # 1 deuce + a natural pair => keep deuce + pair
    Case("2S 9D 9H KC 4C", [0, 1, 2], "1 deuce + pair => hold deuce + pair"),

    # 1 deuce, no pair => keep deuce only
    Case("2S 9D TH KC 4C", [0], "1 deuce no pair => hold deuce only"),
    Case("2S 9D 7D 8S 6D", [0], "1 deuce no pair => hold deuce only"),
    Case("2S 9D 7D 3D KD", [0], "1 deuce no pair => hold deuce only"),

    # --- 0 deuces: (simple sanity around pair prefs)
    Case("AC JC QC TD JD", [0, 1, 2], "3 suited to a royal => go for royal"),
    Case("AS AD 7C 4H 9D", [0, 1], "pair of aces => hold AA"),
    Case("5S 5D KC QH 9D", [0, 1], "pair 3-5 preferred => hold 55"),
    Case("4S 4D 6C 6H 9D", [0, 1], "two pair => keep ONLY one pair; expect lowest per your policy (44)"),
    Case("JS JD 9C 9H 2D", [0, 1, 2, 3, 4], "two pair + deuce, keep full house"),

    # --- made hands (no deuces) that should be held entirely (because evaluator says straight/flush/etc)
    Case("TS JS QS KS AS", [0, 1, 2, 3, 4], "natural royal => hold all"),
    Case("2S 3S 4S 5S 7S", [0, 1, 2, 3, 4], "flush => hold all"),
    Case("3D 4H 5S 6C 7D", [0, 1, 2, 3, 4], "straight => hold all"),

    # --- trips (no deuces): you said "We should not hold all for trips."
    # So these expect holding ONLY the trips, not all 5.
    Case("TD TC TH 7C QC", [0, 1, 2], "trips => hold only trips"),
    Case("9S 9D 9H AD KC", [0, 1, 2], "trips => hold only trips"),
]

# (Add more as you discover interesting edge-cases; 30-ish is a great target.)


def run() -> int:
    fails = 0
    for i, case in enumerate(CASES):
        cards = parse_hand(case.hand)
        got = j_riff_strategy_deuces_wild_bonus(cards).mask
        exp = idxs_to_mask(case.expected_idxs)

        ok = (got == exp)
        if not ok:
            fails += 1
            got_idxs = mask_to_idxs(got)
            print(f"\nFAIL {i:02d}: {case.hand}")
            print(f"  note: {case.note}")
            print(f"  expected: {mask_to_str(exp)}  idxs={case.expected_idxs}")
            print(f"  got:      {mask_to_str(got)}  idxs={got_idxs}")
        else:
            print(f"ok   {i:02d}: {case.hand}  hold={mask_to_str(got)}  {case.note}")

    print(f"\nSummary: {len(CASES) - fails}/{len(CASES)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())

