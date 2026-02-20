import { Suspense, lazy, useState } from "react";
import GamesPage from "./pages/GamesPage";
import { Tabs } from "./components/Tabs";
import "./App.css";

// Lazy load heavier pages
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));

function PageLoading() {
  return (
    <div style={{ padding: 12, fontSize: 13, opacity: 0.85 }}>
      Loading…
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState<"games" | "analytics" | "about">("games");

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      {/* App Title */}
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <h1
          style={{
            fontSize: 32,
            fontWeight: 700,
            margin: 0,
            letterSpacing: 0.5,
          }}
        >
          NBA Odds Analytics Dashboard
        </h1>

        <div
          style={{
            opacity: 0.7,
            fontSize: 14,
            marginTop: 6,
          }}
        >
          Market pricing analysis, strategy performance, and equity tracking.
        </div>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          marginBottom: 20,
        }}
      >
        <Tabs
          value={tab}
          onChange={setTab}
          items={[
            { value: "games", label: "Games" },
            { value: "analytics", label: "Analytics" },
            { value: "about", label: "About" },
          ]}
        />
      </div>

      {tab === "games" && <GamesPage />}

      {tab === "analytics" && (
        <Suspense fallback={<PageLoading />}>
          <AnalyticsPage />
        </Suspense>
      )}

      {tab === "about" && (
        <Suspense fallback={<PageLoading />}>
          <AboutPage />
        </Suspense>
      )}
    </div>
  );
}