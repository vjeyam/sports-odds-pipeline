import { useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";
import { getStrategyRoiBuckets, type RoiBucketRow, type StrategyName } from "../lib/api";

function fmt(x: number | null | undefined, digits = 3) {
  if (x == null) return "—";
  return x.toFixed(digits);
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
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);
      try {
        const res = await getStrategyRoiBuckets(strategy, start, end);
        if (cancelled) return;
        setRows(res.buckets ?? []);
      } catch (e) {
        if (cancelled) return;
        setRows([]);
        setErr(e instanceof Error ? e.message : "Unknown error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [strategy, start, end]);

  const data = useMemo(() => {
    return (rows ?? []).map((r) => ({
      bucket: r.bucket,
      roi: r.roi ?? 0,
    }));
  }, [rows]);

  if (loading) return <div style={{ fontSize: 12, opacity: 0.85 }}>Loading buckets…</div>;
  if (err) return <div style={{ fontSize: 12, opacity: 0.85 }}>Chart error: {err}</div>;
  if (data.length === 0) return <div style={{ fontSize: 12, opacity: 0.85 }}>No bucket data in this range.</div>;

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => fmt(v, 2)} />
          <Tooltip
            formatter={(value: any) => [fmt(value, 3), "ROI"]}
            labelFormatter={(label) => `Bucket: ${label}`}
            contentStyle={{ fontSize: 12 }}
          />

          <Bar dataKey="roi" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.roi >= 0 ? "rgba(96, 165, 250, 0.75)" : "rgba(248, 113, 113, 0.75)"} // blue for positive, red for negative
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}