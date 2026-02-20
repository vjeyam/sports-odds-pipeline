import { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import type { StrategyEquityPoint, StrategyName } from "../lib/api";

function fmtMoney(x: unknown): string {
  const n = typeof x === "number" ? x : null;
  if (n == null) return "—";
  return n >= 0 ? `+${n.toFixed(2)}` : n.toFixed(2);
}

function pct(x: number | null | undefined) {
  if (x == null) return "—";
  return `${(x * 100).toFixed(1)}%`;
}

function fmtX(iso: string | null, idx: number): string {
  if (!iso) return String(idx + 1);
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    timeZone: "America/Chicago",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function stratLabel(s: StrategyName) {
  if (s === "favorite") return "Favorite";
  if (s === "underdog") return "Underdog";
  if (s === "home") return "Home";
  return "Away";
}

export default function StrategyEquityChart({
  strategy,
  equity,
}: {
  strategy: StrategyName;
  equity: StrategyEquityPoint[];
}) {
  const data = useMemo(() => {
    return (equity ?? []).map((p, i) => ({
      x: fmtX(p.commence_time ?? null, i),
      bet_profit: p.bet_profit ?? null,
      cum_profit: p.cum_profit ?? null,
      cum_roi: p.cum_roi ?? null,
    }));
  }, [equity]);

  if (!data.length) {
    return <div style={{ fontSize: 12, opacity: 0.85 }}>No equity points in this range yet.</div>;
  }

  // Muted single line color; keeps dashboard calm
  const LINE = "rgba(96, 165, 250, 0.80)";

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.25)" />
          <XAxis dataKey="x" tick={{ fontSize: 12 }} minTickGap={18} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            labelFormatter={(label) => `${stratLabel(strategy)} • Time (CT): ${label}`}
            formatter={(value: any, name: any, props: any) => {
              if (name === "cum_profit") return [fmtMoney(value), "Cum P/L"];
              if (name === "bet_profit") return [fmtMoney(value), "Bet P/L"];
              if (name === "cum_roi") return [pct(value), "Cum ROI"];
              return [String(value), String(name)];
            }}
            contentStyle={{ fontSize: 12 }}
          />

          <Line
            type="monotone"
            dataKey="cum_profit"
            name="cum_profit"
            stroke={LINE}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}