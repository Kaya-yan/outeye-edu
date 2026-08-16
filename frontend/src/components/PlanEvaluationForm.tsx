"use client";

import { useState } from "react";
import { apiPost } from "@/lib/api";

export default function PlanEvaluationForm({
  chosenVersion,
}: {
  chosenVersion: "basic" | "enhanced";
}) {
  const [sentiment, setSentiment] = useState<"up" | "down" | null>(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (!sentiment && rating === 0 && !comment.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await apiPost("/analysis/ab-evaluate", {
        chosen_version: chosenVersion,
        sentiment: sentiment || undefined,
        rating: rating || undefined,
        comment: comment.trim() || undefined,
      });
      setSubmitted(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "评价提交失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="archive-surface flex items-center gap-2 p-5 text-sm text-sage-700">
        <span>✅</span> 感谢你的评价！
      </div>
    );
  }

  return (
    <div className="archive-surface p-5">
      <div className="section-title mb-3">评价此版本</div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSentiment(sentiment === "up" ? null : "up")}
            className={`flex h-10 w-10 items-center justify-center rounded-full border text-lg transition-colors ${
              sentiment === "up"
                ? "border-sage-500 bg-sage-100"
                : "border-black/10 bg-white hover:border-sage-300"
            }`}
            aria-label="赞成"
          >
            👍
          </button>
          <button
            onClick={() => setSentiment(sentiment === "down" ? null : "down")}
            className={`flex h-10 w-10 items-center justify-center rounded-full border text-lg transition-colors ${
              sentiment === "down"
                ? "border-rose-400 bg-rose-50"
                : "border-black/10 bg-white hover:border-rose-300"
            }`}
            aria-label="反对"
          >
            👎
          </button>
        </div>

        <div className="flex items-center gap-1 text-2xl">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              onClick={() => setRating(n)}
              className={`transition-colors ${
                n <= rating ? "text-accent-500" : "text-ink-200 hover:text-ink-300"
              }`}
              aria-label={`${n} 星`}
            >
              ★
            </button>
          ))}
        </div>
      </div>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="哪里需要改进？"
        rows={2}
        className="morandi-input mt-3"
      />

      {error && <p className="mt-2 text-xs text-rose-600">{error}</p>}

      <button
        onClick={submit}
        disabled={submitting || (!sentiment && rating === 0 && !comment.trim())}
        className="btn-primary mt-3 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "提交中..." : "提交评价"}
      </button>
    </div>
  );
}
