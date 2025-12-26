# vipor/poker/hot_roll.py
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Literal, Optional

Phase = Literal["deal", "draw"]


@dataclass(frozen=True)
class HotRollConfig:
    # Average once every 6 hands:
    p_per_hand: float = 1.0 / 6.0

    # If a roll is scheduled this hand, probability it happens on the deal phase.
    # (Else it happens on draw.)
    p_deal_given_roll: float = 0.5


@dataclass
class HotRollState:
    scheduled_phase: Optional[Phase] = None
    multiplier: Optional[int] = None


def schedule_hot_roll_for_hand(rng: random.Random, cfg: HotRollConfig) -> HotRollState:
    """
    Decide at the start of a hand whether Hot Roll will occur this hand.
    If yes, decide whether it triggers on deal or draw.
    """
    st = HotRollState()
    if rng.random() >= cfg.p_per_hand:
        return st

    st.scheduled_phase = "deal" if (rng.random() < cfg.p_deal_given_roll) else "draw"
    return st


def maybe_trigger_hot_roll(rng: random.Random, st: HotRollState, phase: Phase) -> Optional[int]:
    """
    Trigger Hot Roll on the given phase iff scheduled for this phase and not already triggered.
    Returns multiplier (2..12) if triggered, else None.
    """
    if st.multiplier is not None:
        return None
    if st.scheduled_phase != phase:
        return None

    d1 = rng.randrange(1, 7)
    d2 = rng.randrange(1, 7)
    st.multiplier = d1 + d2
    return st.multiplier


def expected_multiplier_2d6(p_roll: float) -> float:
    """
    Expected value of the multiplier applied to payout when:
      - with probability p_roll, multiplier is (2d6)
      - otherwise multiplier is 1
    E[2d6] = 7, so E[mult] = 1 + p_roll * (7 - 1) = 1 + 6*p_roll
    """
    return 1.0 + 6.0 * p_roll

