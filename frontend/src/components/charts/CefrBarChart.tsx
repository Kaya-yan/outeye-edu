"use client";

import "@/lib/chartjs";
import { Bar } from "react-chartjs-2";
import type { TooltipItem } from "chart.js";

interface CefrBarChartProps {
  distribution: Record<string, number>;
  totalWords: number;
}

const LEVELS = ["A1-A2", "B1-B2", "C1-C2", "未分级"];
const COLORS = ["#cbd6c5", "#d8c46a", "#c7d3d4", "#dccfc8"];
const BORDER_COLORS = ["#96a790", "#c4b257", "#7f8b8d", "#a99893"];

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
          label: (ctx: TooltipItem<"bar">) =>
            `${counts[ctx.dataIndex]} 词 (${(ctx.parsed.x ?? 0).toFixed(1)}%)`,
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
