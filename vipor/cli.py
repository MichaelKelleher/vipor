import argparse
from pathlib import Path

from vipor.poker.paytable import PayTable
from vipor.poker.sim import simulate
from vipor.poker.strategy import hold_any_pair_else_none, hold_nothing

try:
    from vipor.poker.strategy_rules_riff import riff_strategy
except Exception:
    riff_strategy = None

# Capture the actual import error for mc_best so we can show it
_mc_best_import_error = None
try:
    from vipor.poker.best_hold_mc import make_mc_best_strategy
except Exception as e:
    make_mc_best_strategy = None
    _mc_best_import_error = e


def main() -> None:
    ap = argparse.ArgumentParser(description="Vipor — Video Poker Research")

    ap.add_argument(
        "--paytable",
        default=str(Path("paytables") / "9_6_job.yaml"),
        help="Path to paytable YAML",
    )
    ap.add_argument("--hands", type=int, default=100_000, help="Hands to simulate")
    ap.add_argument("--bet", type=int, default=1, help="Bet per hand (coins)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed")
    ap.add_argument("--trace", type=int, default=0, help="Trace first N hands")

    ap.add_argument(
        "--strategy",
        default="any_pair",
        choices=["any_pair", "none", "riff", "j_riff_deuces_wild_bonus", "mc_best"],

    )
    ap.add_argument("--mc_trials", type=int, default=200)

    ap.add_argument(
        "--ruleset",
        default="job",
        choices=["job", "deuces", "deuces_bonus", "j_riff_deuces_wild_bonus"],
    )

    # frozen-hand EV mode
    ap.add_argument("--frozen", help='Freeze a hand like "AS 2H 3C 4D KD"')
    ap.add_argument("--hold_mask", type=int, default=0)
    ap.add_argument("--trials", type=int, default=200_000)

    # --- Hot Roll ---
    ap.add_argument("--hot_roll", action="store_true", help="Enable Hot Roll feature")
    ap.add_argument(
        "--hot_roll_rate",
        type=float,
        default=1.0 / 6.0,
        help="Per-hand Hot Roll incidence (default: 1/6)",
    )
    ap.add_argument(
        "--hot_roll_deal_share",
        type=float,
        default=0.5,
        help="Given a Hot Roll occurs this hand, chance it triggers on deal (else draw)",
    )


    args = ap.parse_args()

    pt = PayTable.from_yaml(args.paytable)

    # evaluator
    if args.ruleset == "job":
        from vipor.poker.hand_eval import evaluate_hand as evaluator
    elif args.ruleset == "deuces":
        from vipor.poker.hand_eval_deuces import evaluate_deuces as evaluator
    else:
        from vipor.poker.hand_eval_deuces_bonus import evaluate_deuces_bonus as evaluator

    # frozen mode
    if args.frozen:
        from vipor.poker.frozen import parse_hand, frozen_ev_mc

        hand = parse_hand(args.frozen)
        res = frozen_ev_mc(
            paytable=pt,
            initial=hand,
            hold_mask=args.hold_mask,
            trials=args.trials,
            bet_per_hand=args.bet,
            seed=args.seed,
        )

        held = [i for i in range(5) if args.hold_mask & (1 << i)]

        print("Frozen:", args.frozen)
        print("Hold mask:", args.hold_mask)
        print("Held indices:", held)
        print("Trials:", res.trials)
        print(f"Avg payout: {res.avg_payout:.6f}")
        print(f"Avg net:    {res.avg_net:.6f}")

        print("\nCategory counts:")
        for k, v in sorted(res.category_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {k:24s} {v:9,d}  {100.0*v/res.trials:6.3f}%")
        return

    hot_roll_cfg = None
    if args.hot_roll:
        from vipor.poker.hot_roll import HotRollConfig
        hot_roll_cfg = HotRollConfig(
            p_per_hand=args.hot_roll_rate,
            p_deal_given_roll=args.hot_roll_deal_share,
        )

    # strategy
    if args.strategy == "any_pair":
        strategy_fn = hold_any_pair_else_none
    elif args.strategy == "none":
        strategy_fn = hold_nothing
    elif args.strategy == "riff":
        if riff_strategy is None:
            raise SystemExit("riff strategy not available")
        strategy_fn = riff_strategy
    elif args.strategy == "j_riff_deuces_wild_bonus":
        # Import lazily to avoid any import-time coupling
        from vipor.poker.strategy_rules_j_riff import j_riff_strategy_deuces_wild_bonus
        strategy_fn = j_riff_strategy_deuces_wild_bonus


    else:
        if make_mc_best_strategy is None:
            raise SystemExit(f"mc_best not available (import failed: {_mc_best_import_error})")
        strategy_fn = make_mc_best_strategy(
            pt,
            evaluator=evaluator,
            trials=args.mc_trials,
            seed=args.seed,
            hot_roll_cfg=hot_roll_cfg if args.hot_roll else None,
            hot_roll_paytable_bet=5,
        )

    hot_roll_cfg = None
    if args.hot_roll:
        from vipor.poker.hot_roll import HotRollConfig
        hot_roll_cfg = HotRollConfig(
            p_per_hand=args.hot_roll_rate,
            p_deal_given_roll=args.hot_roll_deal_share,
        )

    res = simulate(
        pt,
        hands=args.hands,
        bet_per_hand=args.bet,
        seed=args.seed,
        trace_n=args.trace,
        strategy_fn=strategy_fn,
        evaluator=evaluator,
        hot_roll_enabled=args.hot_roll,
        hot_roll_cfg=hot_roll_cfg,
        hot_roll_bet_cost=10,
        hot_roll_paytable_bet=5,
    )

    if args.hot_roll:
        print(f"Hot Roll: enabled  rate={args.hot_roll_rate}  deal_share={args.hot_roll_deal_share}")
        print("Hot Roll: bet_cost=10  paytable_bet=5  multiplier=2d6")

    print(f"Paytable: {pt.name}")
    print(f"Ruleset:  {args.ruleset}")
    print(f"Strategy: {args.strategy}")
    if args.strategy == "mc_best":
        print(f"MC trials per mask: {args.mc_trials}")
    print(f"Hands:    {res.hands:,}")
    print(f"Bet:      {res.total_bet:,}")
    print(f"Payout:   {res.total_payout:,}")
    print(f"Net:      {res.total_net:,}")
    print(f"EV/hand:  {res.ev_per_hand:.6f}")
    print(f"Return%:  {100.0 * res.return_pct:.4f}%")

    print("\nCategory counts:")
    for k in sorted(res.category_counts, key=lambda x: (-res.category_counts[x], x)):
        v = res.category_counts[k]
        print(f"  {k:24s} {v:9,d}  {100.0*v/res.hands:6.3f}%")


if __name__ == "__main__":
    main()

