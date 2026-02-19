import { useState } from "react";
import GamesPage from "./pages/GamesPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import { Tabs } from "./components/Tabs";
import "./App.css";

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

      {tab === "games" ? <GamesPage /> : <AnalyticsPage />}
    </div>
  );
}
