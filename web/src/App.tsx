import { Suspense, lazy, useState } from "react";
import GamesPage from "./pages/GamesPage";
import { Tabs } from "./components/Tabs";
import "./App.css";

const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));

function PageLoading() {
  return (
    <div style={{ padding: 12, fontSize: 13, opacity: 0.85 }}>
      Loading analytics…
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState<"games" | "analytics">("games");

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      <h2>{tab === "games" ? "Games" : "Analytics"}</h2>

      <div style={{ marginBottom: 12 }}>
        <Tabs
          value={tab}
          onChange={setTab}
          items={[
            { value: "games", label: "Games" },
            { value: "analytics", label: "Analytics" },
          ]}
        />
      </div>

      {tab === "games" ? (
        <GamesPage />
      ) : (
        <Suspense fallback={<PageLoading />}>
          <AnalyticsPage />
        </Suspense>
      )}
    </div>
  );
}
