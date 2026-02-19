import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";

type Strategy = "favorite" | "underdog";

type EquityRow = {
  game_index: number;
  commence_time: string;
  cum_profit: number;
};

type EquityResp = {
  strategy: Strategy;
  equity: EquityRow[];
};

async function fetchEquity(
  strategy: Strategy,
  start: string,
  end: string
) {
  const r = await fetch(
    `/api/strategies/equity?strategy=${strategy}&start=${start}&end=${end}`
  );
  if (!r.ok) throw new Error("Failed to fetch equity");
  return (await r.json()) as EquityResp;
}

export default function EquityCurveChart({
  start,
  end,
}: {
  start: string;
  end: string;
}) {
  const [data, setData] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    (async () => {
      try {
        const [fav, dog] = await Promise.all([
          fetchEquity("favorite", start, end),
          fetchEquity("underdog", start, end),
        ]);

        const merged: any[] = [];

        fav.equity.forEach((row, i) => {
          merged.push({
            index: row.game_index,
            label: new Date(row.commence_time).toLocaleDateString(),
            favorite: row.cum_profit,
            underdog: dog.equity[i]?.cum_profit ?? null,
          });
        });

        if (mounted) setData(merged);
      } catch (e: any) {
        if (mounted) setError(e.message);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [start, end]);

  if (error) return <div style={{ color: "tomato" }}>{error}</div>;
  if (!data.length)
    return <div>No decided games yet — equity builds after winners exist.</div>;

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey="label" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="favorite" dot={false} />
          <Line type="monotone" dataKey="underdog" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
