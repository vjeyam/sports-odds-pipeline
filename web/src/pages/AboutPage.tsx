export default function AboutPage() {
  return (
    <div style={{ maxWidth: 820, lineHeight: 1.7 }}>
      <h2 style={{ marginBottom: 8 }}>About This Project</h2>

      <p>
        This project analyzes how efficiently sportsbooks price NBA games and
        evaluates whether simple betting strategies (favorite, underdog, home,
        away) produce positive expected value over time.
      </p>

      <h3 style={{ marginTop: 24 }}>Data Sources</h3>

      <p>
        Odds snapshots come from the{" "}
        <a
          href="https://the-odds-api.com/liveapi/guides/v4/#example-response-5"
          target="_blank"
          rel="noopener noreferrer"
        >
          Odds API
        </a>{" "}
        (FanDuel, DraftKings, BetMGM, and others). Final game results are pulled
        from the{" "}
        <a
          href="https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b"
          target="_blank"
          rel="noopener noreferrer"
        >
          ESPN API
        </a>.
      </p>
      
      <h3 style={{ marginTop: 24 }}>Repository</h3>

      <p>
        View the full source code on{" "}
        <a
          href="https://github.com/vjeyam/sports-odds-pipeline"
          target="_blank"
          rel="noopener noreferrer"
        >
          GitHub
        </a>.
      </p>

      <p style={{ marginTop: 30, opacity: 0.75 }}>
        Built as a portfolio project demonstrating ETL design, analytics
        engineering, and full-stack data product development.
      </p>
    </div>
  );
}