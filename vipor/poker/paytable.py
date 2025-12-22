from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import yaml


@dataclass(frozen=True, slots=True)
class PayTable:
    name: str
    bet_unit: int
    payouts: Dict[str, int]

    @classmethod
    def from_yaml(cls, path: str) -> "PayTable":
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        name = str(data.get("name", "Unnamed PayTable"))
        bet_unit = int(data.get("bet_unit", 1))
        payouts = dict(data.get("payouts", {}))

        if "nothing" not in payouts:
            payouts["nothing"] = 0

        # minimal validation (we’ll tighten later as needed)
        for k, v in payouts.items():
            if not isinstance(k, str):
                raise ValueError("Paytable keys must be strings")
            if not isinstance(v, int) or v < 0:
                raise ValueError(f"Invalid payout for {k}: {v}")

        return cls(name=name, bet_unit=bet_unit, payouts=payouts)

    def payout_for(self, category: str) -> int:
        return int(self.payouts.get(category, 0))

