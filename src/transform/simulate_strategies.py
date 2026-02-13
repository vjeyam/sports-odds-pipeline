import sqlite3
from typing import List, Tuple


def profit(odds: int, stake: float = 1.0) -> float:
    """Return profit only (excluding returned stake)."""
    if odds < 0:
        return stake * (100.0 / abs(odds))
    return stake * (odds / 100.0)


def roi_for(
    rows: List[Tuple],
    strategy: str,
    stake: float = 1.0
) -> Tuple[int, float, float]:
    """
    Compute ROI for a given strategy.

    strategy ∈ {"favorite", "underdog", "home", "away"}
    """
    bankroll = 0.0
    bets = 0

    for fav, dog, winner, home_odds, away_odds in rows:
        bets += 1

        if strategy == "favorite":
            pick = fav
        elif strategy == "underdog":
            pick = dog
        elif strategy == "home":
            pick = "home"
        elif strategy == "away":
            pick = "away"
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        odds = home_odds if pick == "home" else away_odds

        if pick == winner:
            bankroll += profit(odds, stake=stake)
        else:
            bankroll -= stake

    roi = bankroll / (bets * stake) if bets else 0.0
    return bets, bankroll, roi


def simulate(db_path: str = "odds.sqlite", stake: float = 1.0):
    conn = sqlite3.connect(db_path)

    rows = conn.execute("""
    select
      favorite_side,
      underdog_side,
      winner,
      best_home_price_american,
      best_away_price_american
    from fact_game_results_best_market
    """).fetchall()

    for strat in ["favorite", "underdog", "home", "away"]:
        bets, net, roi = roi_for(rows, strat, stake=stake)
        print(f"{strat:8s} | bets={bets:3d} net_profit={net:7.3f} ROI={roi:6.3f}")

    conn.close()


if __name__ == "__main__":
    simulate()
