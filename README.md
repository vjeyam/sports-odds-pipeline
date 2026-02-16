# Sports Market Efficiency & Pricing Analysis

A modular ETL + analytics pipeline for evaluating sports betting market efficiency using:

* [Odds API](https://the-odds-api.com/liveapi/guides/v4/#example-response-5) for real-time odds data
* [ESPN API](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b?permalink_comment_id=5696426&utm_source) for game results
* SQLite data warehouse
* Streamlit dashboard (admin + user modes)

The system supports:

* Close line analytics
* Best-market frequency
* Calibration analysis
* Strategy simulation (ROI, drawdown, profit factor)
* One-click ETL updates from the dashboard

## Setup Instructions

1. Clone the repo and navigate to the project directory:

```bash
git clone https://github.com/vjeyam/sports-odds-etl.git
```

2. Create a virtual environment and install dependencies:

```bash
conda create -n sports-odds python=3.9
conda activate sports-odds
```

```bash
pip install -r requirements.txt
```

3. Set up environment variables for API keys:

In project root:

```.env
ODDS_API_KEY=your_odds_api_key_here
```

4. Run the dashboard:

```bash
streamlit run app.py
```

## Dashboard Features

### User Mode

* View analytics dashboard with close line charts, best-market frequency, and calibration plots
* See strategy performance metrics (ROI, drawdown, profit factor)
* Run one-click ETL updates to refresh data

### Admin Mode

* Change SQLite DB path
* Lock/unlock user updates
* Cancel pipeline runs (soft cancel between stages)
* View:
  * Pipeline row deltas
  * Table row counts
  * Calibration bucket internals
  * Raw data previews
