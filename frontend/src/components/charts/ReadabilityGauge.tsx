"use client";

import "@/lib/chartjs";
import { Doughnut } from "react-chartjs-2";

interface ReadabilityGaugeProps {
  fleschScore: number;
}

function getLevel(score: number): { label: string; color: string } {
  if (score >= 80) return { label: "非常容易", color: "#22c55e" };
  if (score >= 60) return { label: "容易", color: "#4ade80" };
  if (score >= 40) return { label: "中等", color: "#facc15" };
  if (score >= 20) return { label: "困难", color: "#f97316" };
  return { label: "非常困难", color: "#ef4444" };
}

export default function ReadabilityGauge({ fleschScore }: ReadabilityGaugeProps) {
  const clamped = isNaN(fleschScore) ? 0 : Math.max(0, Math.min(100, fleschScore));
  const { label, color } = getLevel(clamped);

  const data = {
    datasets: [
      {
        data: [clamped, 100 - clamped],
        backgroundColor: [color, "rgba(0,0,0,0.05)"],
        borderWidth: 0,
        circumference: 180,
        rotation: 270,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "75%",
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false },
    },
  };

  return (
    <div className="relative h-48 flex flex-col items-center justify-center">
      <Doughnut data={data} options={options} />
      <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
        <span className="text-2xl font-bold" style={{ color }}>{clamped.toFixed(0)}</span>
        <span className="text-xs text-gray-500">{label}</span>
      </div>
    </div>
  );
}
