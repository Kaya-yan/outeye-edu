"use client";

import React, { useState, useEffect } from "react";
import { apiPost, apiGet } from "@/lib/api";

interface ReviewStats {
  total_reviews: number;
  avg_total: number;
  avg_objective: number;
  avg_activity: number;
  avg_theory: number;
  avg_differentiation: number;
  avg_practicability: number;
  recent_reviews: Array<{
    reviewer_name: string;
    reviewer_title: string;
    score_total: number;
    comments: string;
  }>;
}

interface ReviewForm {
  plan_id: string;
  reviewer_name: string;
  reviewer_title: string;
  reviewer_institution: string;
  score_objective: number;
  score_activity: number;
  score_theory: number;
  score_differentiation: number;
  score_practicability: number;
  comments: string;
  suggestion: string;
}

const DIMENSIONS = [
  { key: "score_objective", label: "教学目标合理性", desc: "教案目标是否明确、可衡量、符合学生水平" },
  { key: "score_activity", label: "活动设计质量", desc: "课堂活动是否具体、可操作、覆盖多种技能" },
  { key: "score_theory", label: "理论依据充分性", desc: "教学建议是否有理论支撑和数据依据" },
  { key: "score_differentiation", label: "差异化考虑", desc: "是否针对不同水平学生设计分层活动" },
  { key: "score_practicability", label: "课堂可实施性", desc: "活动设计是否可在实际课堂中执行" },
];

export default function ExpertReviewPage() {
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<ReviewForm>({
    plan_id: "",
    reviewer_name: "",
    reviewer_title: "",
    reviewer_institution: "",
    score_objective: 4,
    score_activity: 4,
    score_theory: 4,
    score_differentiation: 4,
    score_practicability: 4,
    comments: "",
    suggestion: "",
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await apiGet<ReviewStats>("/expert-review/stats");
      setStats(data);
    } catch (e) {
      console.error("Failed to load stats:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!form.plan_id.trim() || !form.reviewer_name.trim()) {
      setError("请填写教案ID和评审专家姓名");
      return;
    }

    setError("");
    setSubmitting(true);
    try {
      await apiPost("/expert-review/submit", form);
      setSubmitted(true);
      loadStats();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const updateScore = (key: string, value: number) => {
    setForm({ ...form, [key]: value });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">专家评审系统</h1>
          <p className="text-sm text-gray-500 mt-1">
            五维度专家评分，验证教案质量与平台可信度
          </p>
        </div>

        {/* Stats Section */}
        {loading ? (
          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
            加载统计数据...
          </div>
        ) : stats && stats.total_reviews > 0 ? (
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-200 p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">评审统计</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
              <div className="text-center">
                <div className="text-3xl font-extrabold text-amber-600">{stats.total_reviews}</div>
                <div className="text-xs text-gray-500">评审总数</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-extrabold text-amber-600">{stats.avg_total}<span className="text-sm">/5.0</span></div>
                <div className="text-xs text-gray-500">综合平均分</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-extrabold text-amber-600">{stats.avg_activity}<span className="text-sm">/5.0</span></div>
                <div className="text-xs text-gray-500">活动设计</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-extrabold text-amber-600">{stats.avg_practicability}<span className="text-sm">/5.0</span></div>
                <div className="text-xs text-gray-500">可实施性</div>
              </div>
            </div>

            {/* Dimension Scores */}
            <div className="space-y-2">
              {[
                { label: "教学目标", score: stats.avg_objective },
                { label: "活动设计", score: stats.avg_activity },
                { label: "理论依据", score: stats.avg_theory },
                { label: "差异化", score: stats.avg_differentiation },
                { label: "可实施性", score: stats.avg_practicability },
              ].map((dim) => (
                <div key={dim.label} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-16">{dim.label}</span>
                  <div className="flex-1 h-2 bg-white rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-400 rounded-full"
                      style={{ width: `${(dim.score / 5) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-gray-700 w-8">{dim.score}</span>
                </div>
              ))}
            </div>

            {/* Recent Reviews */}
            {stats.recent_reviews.length > 0 && (
              <div className="mt-4 pt-4 border-t border-amber-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">最近评审</h3>
                <div className="space-y-2">
                  {stats.recent_reviews.map((r, i) => (
                    <div key={i} className="flex items-center gap-3 text-sm">
                      <span className="font-medium text-gray-800">{r.reviewer_name}</span>
                      {r.reviewer_title && <span className="text-gray-400">({r.reviewer_title})</span>}
                      <span className="ml-auto font-bold text-amber-600">{r.score_total}/5.0</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6 text-center text-gray-500">
            暂无评审数据，成为第一位评审专家！
          </div>
        )}

        {/* Submit Form */}
        {submitted ? (
          <div className="bg-green-50 rounded-xl border border-green-200 p-8 text-center">
            <div className="text-4xl mb-4">✅</div>
            <h2 className="text-xl font-bold text-green-800 mb-2">评审提交成功！</h2>
            <p className="text-green-700">感谢您的专业评审，您的意见将帮助我们改进教案质量。</p>
            <button
              onClick={() => { setSubmitted(false); setForm({ ...form, plan_id: "", comments: "", suggestion: "" }); }}
              className="mt-4 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              继续评审
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">提交评审</h2>

            {/* Reviewer Info */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">教案ID *</label>
                <input
                  type="text"
                  value={form.plan_id}
                  onChange={(e) => setForm({ ...form, plan_id: e.target.value })}
                  placeholder="关联的教案ID或标题"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">专家姓名 *</label>
                <input
                  type="text"
                  value={form.reviewer_name}
                  onChange={(e) => setForm({ ...form, reviewer_name: e.target.value })}
                  placeholder="您的姓名"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">职称</label>
                <input
                  type="text"
                  value={form.reviewer_title}
                  onChange={(e) => setForm({ ...form, reviewer_title: e.target.value })}
                  placeholder="教授/副教授/讲师等"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                />
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">所在单位</label>
              <input
                type="text"
                value={form.reviewer_institution}
                onChange={(e) => setForm({ ...form, reviewer_institution: e.target.value })}
                placeholder="大学/研究机构"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
              />
            </div>

            {/* Scoring Dimensions */}
            <h3 className="text-sm font-semibold text-gray-700 mb-3">评分（1-5分）</h3>
            <div className="space-y-4 mb-6">
              {DIMENSIONS.map((dim) => (
                <div key={dim.key} className="flex items-center gap-4">
                  <div className="w-32">
                    <div className="text-sm font-medium text-gray-700">{dim.label}</div>
                    <div className="text-[10px] text-gray-400">{dim.desc}</div>
                  </div>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((v) => (
                      <button
                        key={v}
                        onClick={() => updateScore(dim.key, v)}
                        className={`w-10 h-10 rounded-lg text-sm font-bold transition-colors ${
                          form[dim.key as keyof ReviewForm] === v
                            ? "bg-amber-500 text-white"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        }`}
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                  <span className="text-sm font-bold text-amber-600 w-8">
                    {form[dim.key as keyof ReviewForm] as number}/5
                  </span>
                </div>
              ))}
            </div>

            {/* Comments */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">评审意见</label>
              <textarea
                value={form.comments}
                onChange={(e) => setForm({ ...form, comments: e.target.value })}
                placeholder="对教案的整体评价..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
              />
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">改进建议</label>
              <textarea
                value={form.suggestion}
                onChange={(e) => setForm({ ...form, suggestion: e.target.value })}
                placeholder="具体的改进建议..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
              />
            </div>

            {error && (
              <div className="mb-4 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {submitting ? "提交中..." : "提交评审"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
