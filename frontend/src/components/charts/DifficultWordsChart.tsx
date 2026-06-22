"use client";

import "@/lib/chartjs";
import { Bar } from "react-chartjs-2";

interface DifficultWord {
  word: string;
  level: string;
  count: number;
  in_awl: boolean;
}

interface DifficultWordsChartProps {
  words: DifficultWord[];
}

const LEVEL_COLORS: Record<string, string> = {
  C1: "#ef4444",
  C2: "#dc2626",
  B2: "#f97316",
  unknown: "#9ca3af",
};

export default function DifficultWordsChart({ words }: DifficultWordsChartProps) {
  const top10 = words.slice(0, 10).reverse();

  const data = {
    labels: top10.map((w) => w.word),
    datasets: [
      {
        label: "出现次数",
        data: top10.map((w) => w.count),
        backgroundColor: top10.map((w) => LEVEL_COLORS[w.level] || "#9ca3af"),
        borderRadius: 4,
        barThickness: 16,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: "y" as const,
    scales: {
      x: {
        beginAtZero: true,
        ticks: { stepSize: 1 },
        grid: { color: "rgba(0,0,0,0.04)" },
      },
      y: {
        grid: { display: false },
        ticks: { font: { size: 11 } },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          afterLabel: (ctx: { dataIndex: number }) => {
            const w = top10[ctx.dataIndex];
            return `${w.level}${w.in_awl ? " | AWL" : ""}`;
          },
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
