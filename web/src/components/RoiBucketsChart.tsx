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
  ReferenceLine,
  Legend,
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

function money(x: number | null | undefined) {
  if (x == null) return "—";
  return x >= 0 ? `+${x.toFixed(2)}` : x.toFixed(2);
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
  const [showTable, setShowTable] = useState(false);

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
      n_bets: r.n_bets ?? 0,
      wins: r.wins ?? 0,
      win_rate: r.win_rate ?? null,
      profit: r.profit ?? null,
    }));
  }, [rows]);

  if (loading) return <div style={{ fontSize: 12, opacity: 0.85 }}>Loading buckets…</div>;
  if (err) return <div style={{ fontSize: 12, opacity: 0.85 }}>Chart error: {err}</div>;
  if (data.length === 0) return <div style={{ fontSize: 12, opacity: 0.85 }}>No bucket data in this range.</div>;

  const POS = "rgba(96, 165, 250, 0.75)"; // muted blue
  const NEG = "rgba(248, 113, 113, 0.75)"; // muted red
  const BETS = "rgba(255,255,255,0.22)";   // muted gray

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {/* In-chart toggle */}
      <button
        type="button"
        onClick={() => setShowTable((v) => !v)}
        style={{
          position: "absolute",
          top: 8,
          right: 8,
          zIndex: 5,
          padding: "6px 10px",
          borderRadius: 10,
          border: "1px solid rgba(255,255,255,0.14)",
          background: "rgba(255,255,255,0.06)",
          color: "inherit",
          cursor: "pointer",
          fontSize: 12,
          opacity: 0.95,
        }}
        title="Toggle bucket details"
      >
        {showTable ? "Hide table" : "Show table"}
      </button>

      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <ReferenceLine y={0} yAxisId="roi" stroke="rgba(255,255,255,0.25)" />

          <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />

          {/* Left axis = ROI */}
          <YAxis
            yAxisId="roi"
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => fmt(v, 2)}
          />

          {/* Right axis = Bets */}
          <YAxis
            yAxisId="bets"
            orientation="right"
            tick={{ fontSize: 12, opacity: 0.85 }}
            allowDecimals={false}
          />

          <Tooltip
            contentStyle={{ fontSize: 12 }}
            labelFormatter={(label) => `Bucket: ${label}`}
            formatter={(value: any, name: any, payload: any) => {
              if (name === "roi") return [fmt(value, 3), "ROI"];
              if (name === "n_bets") return [String(value), "Bets"];
              return [String(value), String(name)];
            }}
          />

          <Legend
            verticalAlign="bottom"
            align="center"
            wrapperStyle={{ fontSize: 12, opacity: 0.9 }}
            formatter={(value) => (value === "roi" ? "ROI" : "Bets")}
          />

          {/* Bets series (muted, right axis). Draw first so ROI sits on top. */}
          <Bar
            dataKey="n_bets"
            yAxisId="bets"
            name="n_bets"
            fill={BETS}
            radius={[6, 6, 0, 0]}
            barSize={18}
          />

          {/* ROI series (colored, left axis) */}
          <Bar
            dataKey="roi"
            yAxisId="roi"
            name="roi"
            radius={[6, 6, 0, 0]}
            barSize={32}
          >
            {data.map((entry, idx) => (
              <Cell key={`cell-${idx}`} fill={entry.roi >= 0 ? POS : NEG} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Overlay table */}
      {showTable && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 4,
            background: "rgba(0,0,0,0.55)",
            backdropFilter: "blur(2px)",
            borderRadius: 14,
            padding: 12,
            overflow: "auto",
          }}
          onClick={() => setShowTable(false)}
          role="button"
          tabIndex={0}
          title="Click to close"
        >
          <div
            style={{
              background: "rgba(20,20,20,0.85)",
              border: "1px solid rgba(255,255,255,0.10)",
              borderRadius: 12,
              padding: 12,
            }}
            onClick={(e) => e.stopPropagation()}
            role="presentation"
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ fontWeight: 700 }}>Bucket details</div>
              <div style={{ marginLeft: "auto" }}>
                <button
                  type="button"
                  onClick={() => setShowTable(false)}
                  style={{
                    padding: "6px 10px",
                    borderRadius: 10,
                    border: "1px solid rgba(255,255,255,0.14)",
                    background: "rgba(255,255,255,0.06)",
                    color: "inherit",
                    cursor: "pointer",
                    fontSize: 12,
                  }}
                >
                  Close
                </button>
              </div>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ textAlign: "left" }}>
                    {["Bucket", "Bets", "Wins", "Win %", "Profit", "ROI ($1)"].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "8px 10px",
                          borderBottom: "1px solid rgba(255,255,255,0.14)",
                          opacity: 0.9,
                          fontWeight: 650,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.map((b) => (
                    <tr key={b.bucket}>
                      <td style={{ padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.10)" }}>{b.bucket}</td>
                      <td style={{ padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.10)" }}>{b.n_bets}</td>
                      <td style={{ padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.10)" }}>{b.wins}</td>
                      <td style={{ padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.10)" }}>{pct(b.win_rate)}</td>
                      <td style={{ padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.10)" }}>{money(b.profit)}</td>
                      <td style={{ padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.10)" }}>{money(b.roi)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ marginTop: 8, opacity: 0.75, fontSize: 11 }}>
              Tip: click outside the panel to close.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}