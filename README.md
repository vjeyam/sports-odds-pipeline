# sports-odds-etl

To run the ETL pipeline, follow these steps:

```bash
# 1) Pull latest odds snapshot
python -m src.pipelines.run_odds_snapshot --sport basketball_nba --regions us --db odds.sqlite

# 2) Pull results
python -m src.pipelines.run_espn_results_pull --db odds.sqlite

# 3) Build mapping + fact tables
python -m src.transform.build_game_id_map
python -m src.transform.build_fact_game_results_best_market

# 4) Run analytics
python -m src.transform.simulate_strategies
```
