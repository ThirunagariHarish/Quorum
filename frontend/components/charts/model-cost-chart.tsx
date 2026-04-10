"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ModelCostChartProps {
  data: { model: string; cost: number }[];
}

export function ModelCostChart({ data }: ModelCostChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis
          dataKey="model"
          tick={{ fontSize: 12 }}
          className="text-muted-foreground"
        />
        <YAxis
          tick={{ fontSize: 12 }}
          tickFormatter={(v) => `$${v}`}
          className="text-muted-foreground"
        />
        <Tooltip
          formatter={(value) => [`$${Number(value).toFixed(2)}`, "Cost"]}
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px",
            fontSize: "12px",
          }}
        />
        <Bar
          dataKey="cost"
          fill="hsl(var(--primary))"
          radius={[6, 6, 0, 0]}
          maxBarSize={60}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
