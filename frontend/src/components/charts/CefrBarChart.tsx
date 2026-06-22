"use client";

import "@/lib/chartjs";
import { Bar } from "react-chartjs-2";

interface CefrBarChartProps {
  distribution: Record<string, number>;
  totalWords: number;
}

const LEVELS = ["A1-A2", "B1-B2", "C1-C2", "未分级"];
const COLORS = ["#4ade80", "#facc15", "#f87171", "#d1d5db"];
const BORDER_COLORS = ["#22c55e", "#eab308", "#ef4444", "#9ca3af"];

export default function CefrBarChart({ distribution, totalWords }: CefrBarChartProps) {
  const counts = LEVELS.map((l) => distribution[l] || 0);
  const percentages = counts.map((c) => (totalWords > 0 ? (c / totalWords) * 100 : 0));

  const data = {
    labels: LEVELS,
    datasets: [
      {
        label: "占比 (%)",
        data: percentages,
        backgroundColor: COLORS,
        borderColor: BORDER_COLORS,
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: "y" as const,
    scales: {
      x: {
        max: 100,
        ticks: { callback: (v: string | number) => `${v}%` },
        grid: { color: "rgba(0,0,0,0.04)" },
      },
      y: {
        grid: { display: false },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          label: (ctx: any) =>
            `${counts[ctx.dataIndex]} 词 (${ctx.parsed.x.toFixed(1)}%)`,
        },
      },
    },
  };

  return (
    <div className="h-64">
      <Bar data={data} options={options} />
    </div>
  );
}
