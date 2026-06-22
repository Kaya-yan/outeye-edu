"use client";

import "@/lib/chartjs";
import { Radar } from "react-chartjs-2";

interface RadarChartProps {
  vocabulary: { total_words: number; awl_ratio: number; vocabulary_richness: number };
  syntax: { avg_sentence_length: number; flesch_reading_ease: number; long_sentences_count: number };
  discourse: { connective_density: number };
}

export default function RadarChart({ vocabulary, syntax, discourse }: RadarChartProps) {
  const awlScore = Math.max(0, Math.min(vocabulary.awl_ratio * 500, 100));
  const richnessScore = Math.max(0, Math.min(vocabulary.vocabulary_richness * 100, 100));
  const sentenceScore = Math.max(0, Math.min((syntax.avg_sentence_length / 40) * 100, 100));
  const fleschScore = Math.max(0, Math.min(100 - syntax.flesch_reading_ease, 100));
  const longSentScore = Math.max(0, Math.min(syntax.long_sentences_count * 10, 100));
  const connectiveScore = Math.max(0, Math.min(discourse.connective_density * 20, 100));

  const data = {
    labels: ["学术词汇", "词汇丰富度", "句法复杂度", "阅读难度", "长句密度", "连接词密度"],
    datasets: [
      {
        label: "分析维度",
        data: [awlScore, richnessScore, sentenceScore, fleschScore, longSentScore, connectiveScore],
        backgroundColor: "rgba(99, 102, 241, 0.15)",
        borderColor: "rgba(99, 102, 241, 0.8)",
        borderWidth: 2,
        pointBackgroundColor: "rgba(99, 102, 241, 1)",
        pointRadius: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        ticks: { stepSize: 20, display: false },
        grid: { color: "rgba(0,0,0,0.06)" },
        pointLabels: { font: { size: 11 } },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: { parsed: { r: number } }) => `${ctx.parsed.r.toFixed(0)}分`,
        },
      },
    },
  };

  return (
    <div className="h-64">
      <Radar data={data} options={options} />
    </div>
  );
}
