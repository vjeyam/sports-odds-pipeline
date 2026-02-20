# Sports Odds Pipeline (NBA)

ETL + analytics pipeline that tracks NBA moneyline odds across sportsbooks, stores the best available price over time, pulls in game results, and serves everything through a React dashboard.

The point is to see how well the market prices games and whether simple strategies (favorite, underdog, home, away) hold up over time.

## What it does

Odds snapshots come from the [Odds API](https://the-odds-api.com/liveapi/guides/v4/#example-response-5) (FanDuel, DraftKings, BetMGM, and others) and game results from the [ESPN API](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b?permalink_comment_id=5696426&utm_source). Both get transformed and stored in Postgres. The React frontend hits a Spring Boot API, which delegates data/ETL work to a Python FastAPI service.

**ETL (Python)**

- Pulls moneyline snapshots and builds closing lines + best available price across books
- Maps game results back to odds events
- Produces analytics tables: daily summaries, strategy performance, equity curves, ROI by implied probability bucket

**Dashboard (React)**

- Games page — browse games with best moneyline, score, result
- Analytics page — KPI tiles, strategy table, equity curves, daily trend, ROI by probability bucket

## Stack

- **Frontend:** React + Vite + TypeScript + Recharts
- **API layer:** Spring Boot (REST endpoints, routes requests to Python service)
- **Data/ETL service:** Python + FastAPI
- **Database:** PostgreSQL (Docker)
- **CI:** GitHub Actions

## Running locally

**Requirements:** Python 3.9+, Node 18+, Docker

**1. Setup**

Clone the repository:

```bash
git clone https://github.com/vjeyam/sports-odds-pipeline.git
```

Create a virtual enviornment:

```bash
conda create -n nba-pipeline python=3.9
conda activate nba-pipeline
```

Install dependencies at the root of the directory

```bash
pip install -r requirements.txt
npm install
```

Run the server:

```bash
npm run dev
```

Frontend runs at `http://localhost:5173`, Spring Boot at `8080`, Python service at `8000`.

**Environment variables** — create a `.env` in the project root:

```
ODDS_API_KEY=your_key_here
DATABASE_URL=postgresql://localhost:5432/sportsodds
```

## Notes

- The ETL can be triggered manually from the dashboard or run on a schedule via the GitHub Actions workflow in `.github/workflows/`
- Odds data is NBA moneyline only for now
