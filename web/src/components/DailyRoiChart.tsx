import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Legend,
} from "recharts";
import type { AnalyticsDailyRow } from "../lib/api";

function fmtMoney(x: unknown): string {
  const n = typeof x === "number" ? x : null;
  if (n == null) return "—";
  return n >= 0 ? `+${n.toFixed(2)}` : n.toFixed(2);
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return iso;
  return `${iso.slice(5, 7)}-${iso.slice(8, 10)}`;
}

type Metric = "roi" | "profit";

export default function DailyRoiChart({ daily }: { daily: AnalyticsDailyRow[] }) {
  const [metric, setMetric] = useState<Metric>("roi");

  const data = useMemo(() => {
    return (daily ?? []).map((d) => {
      const decided = d.n_decided_games ?? 0;

      // ROI here is avg profit per $1 bet, so estimated daily profit = ROI * decided games
      const favRoi = d.favorite_roi ?? null;
      const dogRoi = d.underdog_roi ?? null;

      const favProfit = favRoi == null ? null : favRoi * decided;
      const dogProfit = dogRoi == null ? null : dogRoi * decided;

      return {
        date: d.date,
        x: fmtDate(d.date),
        decided,

        favorite_roi: favRoi,
        underdog_roi: dogRoi,

        favorite_profit: favProfit,
        underdog_profit: dogProfit,
      };
    });
  }, [daily]);

  const hasAny =
    metric === "roi"
      ? data.some((d) => d.favorite_roi != null || d.underdog_roi != null)
      : data.some((d) => d.favorite_profit != null || d.underdog_profit != null);

  if (!data.length || !hasAny) {
    return <div style={{ fontSize: 12, opacity: 0.85 }}>No daily data for this range.</div>;
  }

  const FAV = "rgba(96, 165, 250, 0.80)"; // muted blue
  const DOG = "rgba(34, 197, 94, 0.70)";  // muted green

  const favKey = metric === "roi" ? "favorite_roi" : "favorite_profit";
  const dogKey = metric === "roi" ? "underdog_roi" : "underdog_profit";

  const subtitle =
    metric === "roi"
      ? "Average ROI ($1) per bet by day."
      : "Estimated profit by day (ROI × decided games).";

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {/* Toggle in chart */}
      <div style={{ position: "absolute", top: 8, right: 8, zIndex: 5 }}>
        <div
          style={{
            display: "inline-flex",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 12,
            overflow: "hidden",
            background: "rgba(255,255,255,0.03)",
          }}
          title="Switch daily chart metric"
        >
          <button
            type="button"
            onClick={() => setMetric("roi")}
            style={{
              padding: "6px 10px",
              border: 0,
              background: metric === "roi" ? "rgba(255,255,255,0.10)" : "transparent",
              color: "inherit",
              cursor: "pointer",
              fontSize: 12,
              opacity: metric === "roi" ? 1 : 0.85,
            }}
          >
            ROI
          </button>
          <button
            type="button"
            onClick={() => setMetric("profit")}
            style={{
              padding: "6px 10px",
              border: 0,
              background: metric === "profit" ? "rgba(255,255,255,0.10)" : "transparent",
              color: "inherit",
              cursor: "pointer",
              fontSize: 12,
              opacity: metric === "profit" ? 1 : 0.85,
            }}
          >
            Profit
          </button>
        </div>
      </div>

      {/* Small hint under toggle (optional subtle) */}
      <div style={{ position: "absolute", top: 40, right: 10, zIndex: 5, fontSize: 11, opacity: 0.65 }}>
        {subtitle}
      </div>

      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.25)" />
          <XAxis dataKey="x" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => fmtMoney(v)} />

          <Tooltip
            labelFormatter={(label, payload) => {
              const full = payload?.[0]?.payload?.date ?? label;
              const decided = payload?.[0]?.payload?.decided ?? 0;
              return `Date: ${full} • Decided: ${decided}`;
            }}
            formatter={(value: any, name: any) => {
              if (name === favKey) return [fmtMoney(value), metric === "roi" ? "Favorite ROI" : "Favorite Profit"];
              if (name === dogKey) return [fmtMoney(value), metric === "roi" ? "Underdog ROI" : "Underdog Profit"];
              return [String(value), String(name)];
            }}
            contentStyle={{ fontSize: 12 }}
          />

          <Legend verticalAlign="bottom" align="center" wrapperStyle={{ fontSize: 12, opacity: 0.9 }} />

          <Line
            type="monotone"
            dataKey={favKey}
            name={metric === "roi" ? "Favorite ROI" : "Favorite Profit"}
            stroke={FAV}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey={dogKey}
            name={metric === "roi" ? "Underdog ROI" : "Underdog Profit"}
            stroke={DOG}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}