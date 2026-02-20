import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { getStrategyEquity, type StrategyEquityPoint } from "../lib/api";

type Props = {
  start: string;
  end: string;
};

type SeriesPoint = {
  x: string; // label
  favorite: number | null;
  underdog: number | null;
};

function fmtX(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  // Show CT-ish date/time compactly
  return d.toLocaleString("en-US", {
    timeZone: "America/Chicago",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtMoney(x: unknown): string {
  const n = typeof x === "number" ? x : null;
  if (n == null) return "—";
  return n >= 0 ? `+${n.toFixed(2)}` : n.toFixed(2);
}

export default function EquityCurveChart({ start, end }: Props) {
  const [fav, setFav] = useState<StrategyEquityPoint[]>([]);
  const [dog, setDog] = useState<StrategyEquityPoint[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setErr(null);
      try {
        const [f, u] = await Promise.all([
          getStrategyEquity("favorite", start, end),
          getStrategyEquity("underdog", start, end),
        ]);
        if (cancelled) return;
        setFav(f.equity ?? []);
        setDog(u.equity ?? []);
      } catch (e) {
        if (cancelled) return;
        setFav([]);
        setDog([]);
        setErr(e instanceof Error ? e.message : "Unknown error");
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [start, end]);

  const data: SeriesPoint[] = useMemo(() => {
    const n = Math.max(fav.length, dog.length);
    const out: SeriesPoint[] = [];
    for (let i = 0; i < n; i++) {
      const fp = fav[i];
      const up = dog[i];
      const label = fmtX(fp?.commence_time ?? up?.commence_time ?? null);
      out.push({
        x: label || String(i + 1),
        favorite: fp?.cum_profit ?? null,
        underdog: up?.cum_profit ?? null,
      });
    }
    return out;
  }, [fav, dog]);

  // legend key
  const FAVORITE_COLOR = "#4F8CFF"; // blue
  const UNDERDOG_COLOR = "#22C55E"; // green

  if (err) {
    return <div style={{ fontSize: 12, opacity: 0.85 }}>Chart error: {err}</div>;
  }

  if (data.length === 0) {
    return <div style={{ fontSize: 12, opacity: 0.85 }}>No equity points in this range yet.</div>;
  }

  return (
    <div style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <XAxis dataKey="x" tick={{ fontSize: 12 }} minTickGap={18} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(v) => fmtMoney(v)}
            labelFormatter={(label) => `Time (CT): ${label}`}
          />
          <Legend
            verticalAlign="bottom"
            align="center"
            wrapperStyle={{ fontSize: 12, opacity: 0.9 }}
          />
          <Line
            type="monotone"
            dataKey="favorite"
            name="Favorite"
            stroke={FAVORITE_COLOR}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="underdog"
            name="Underdog"
            stroke={UNDERDOG_COLOR}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}