import { useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { getStrategyRoiBuckets, type RoiBucketRow, type StrategyName } from "../lib/api";

function fmt(x: number | null | undefined, digits = 3) {
  if (x == null) return "—";
  return x.toFixed(digits);
}

function pct(x: number | null | undefined) {
  if (x == null) return "—";
  return `${(x * 100).toFixed(1)}%`;
}

export default function RoiBucketsChart({
  strategy,
  start,
  end,
}: {
  strategy: StrategyName;
  start: string;
  end: string;
}) {
  const [rows, setRows] = useState<RoiBucketRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const resp = await getStrategyRoiBuckets(strategy, start, end, 0.05, 0.40, 0.80);
        if (mounted) setRows(resp.buckets);
      } catch (e) {
        if (mounted) setErr(e instanceof Error ? e.message : "Unknown error");
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [strategy, start, end]);

  const data = useMemo(
    () =>
      rows.map((r) => ({
        bucket: r.bucket,
        roi: r.roi ?? 0, // recharts needs a number
        roi_raw: r.roi,
        n_bets: r.n_bets,
        wins: r.wins,
        win_rate: r.win_rate,
        profit: r.profit,
      })),
    [rows]
  );

  const hasAnyBets = rows.some((r) => r.n_bets > 0);

  if (loading) return <div style={{ opacity: 0.8 }}>Loading ROI buckets…</div>;
  if (err) return <div style={{ color: "tomato" }}>ROI buckets error: {err}</div>;
  if (!rows.length || !hasAnyBets) {
    return <div style={{ opacity: 0.8 }}>No decided games in this range yet.</div>;
  }

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey="bucket" />
          <YAxis tickFormatter={(v) => (typeof v === "number" ? v.toFixed(2) : String(v))} />
          <Tooltip
            formatter={(value: any, name: any, props: any) => {
              // We only have one bar series ("roi"), but keep this generic.
              if (name === "roi") {
                const p = props?.payload;
                const n = p?.n_bets ?? 0;

                if (!n) {
                  return ["No bets", "ROI ($1)"];
                }

                return [fmt(p?.roi_raw, 3), "ROI ($1)"];
              }
              return [value, name];
            }}
            labelFormatter={(label, payload) => {
              const p = payload?.[0]?.payload;
              if (!p) return `Implied prob bucket: ${label}`;

              const n = p.n_bets ?? 0;
              const wins = p.wins ?? 0;

              if (!n) return `Implied prob bucket: ${label} (0 bets)`;

              return `Implied prob bucket: ${label} (${n} bets, ${wins} wins, win ${pct(
                p.win_rate
              )})`;
            }}
          />
          <Bar dataKey="roi" name="ROI ($1)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}