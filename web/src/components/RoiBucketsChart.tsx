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
        roi: r.roi ?? 0,      // recharts needs a number
        roi_raw: r.roi,       // keep for tooltip
        n_bets: r.n_bets,
        win_rate: r.win_rate,
      })),
    [rows]
  );

  if (loading) return <div style={{ opacity: 0.8 }}>Loading ROI buckets…</div>;
  if (err) return <div style={{ color: "tomato" }}>ROI buckets error: {err}</div>;
  if (!rows.length || rows.every((r) => r.n_bets === 0))
    return <div style={{ opacity: 0.8 }}>No decided games in this range yet.</div>;

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey="bucket" />
          <YAxis />
          <Tooltip
            formatter={(value: any, name: any, props: any) => {
              if (name === "roi") {
                const raw = props?.payload?.roi_raw;
                return [raw == null ? "—" : raw.toFixed(3), "ROI ($1)"];
              }
              return [value, name];
            }}
            labelFormatter={(label) => `Implied prob bucket: ${label}`}
          />
          <Bar dataKey="roi" name="ROI ($1)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}