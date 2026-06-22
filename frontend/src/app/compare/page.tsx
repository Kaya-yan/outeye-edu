"use client";

import React, { useState } from "react";
import { apiPost } from "@/lib/api";

interface CompareResult {
  title: string;
  error?: string;
  text_level?: string;
  language?: string;
  language_name?: string;
  metrics?: {
    total_words: number;
    unique_words: number;
    vocabulary_richness: number;
    awl_ratio: number;
    avg_sentence_length: number;
    flesch_reading_ease: number;
    long_sentences_count: number;
    connective_density: number;
    paragraph_count: number;
    genre_hint: string;
    text_structure?: string;
  };
  cefr_distribution?: Record<string, number>;
  difficult_words_count?: number;
  enhancement_tags?: string[];
  tag_labels?: Record<string, string>;
}

interface CompareResponse {
  results: CompareResult[];
  summary: {
    level_range?: string;
    word_count_range?: string;
    readability_range?: string;
    recommendation?: string;
    error?: string;
  };
  count: number;
}

const CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];

export default function ComparePage() {
  const [studentLevel, setStudentLevel] = useState("B1");
  const [texts, setTexts] = useState([
    { title: "", text: "" },
    { title: "", text: "" },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CompareResponse | null>(null);

  const addText = () => {
    if (texts.length < 5) {
      setTexts([...texts, { title: "", text: "" }]);
    }
  };

  const removeText = (index: number) => {
    if (texts.length > 2) {
      setTexts(texts.filter((_, i) => i !== index));
    }
  };

  const updateText = (index: number, field: "title" | "text", value: string) => {
    const newTexts = [...texts];
    newTexts[index][field] = value;
    setTexts(newTexts);
  };

  const handleCompare = async () => {
    const validTexts = texts.filter((t) => t.text.trim().length >= 20);
    if (validTexts.length < 2) {
      setError("至少需要2篇课文（每篇至少20字）");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const res = await apiPost<CompareResponse>("/analysis/compare", {
        texts: validTexts,
        student_level: studentLevel,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "对比分析失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">教材对比分析</h1>
          <p className="text-sm text-gray-500 mt-1">
            对比多篇课文的难度指标，帮助选择合适的教材
          </p>
        </div>

        {/* Input Section */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">输入课文</h2>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">学生水平</label>
                <select
                  value={studentLevel}
                  onChange={(e) => setStudentLevel(e.target.value)}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-lg"
                >
                  {CEFR_LEVELS.map((l) => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={addText}
                disabled={texts.length >= 5}
                className="px-3 py-1 text-sm text-primary border border-primary/30 rounded-lg hover:bg-primary/5 disabled:opacity-50"
              >
                + 添加课文
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {texts.map((t, i) => (
              <div key={i} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">课文 {i + 1}</span>
                  {texts.length > 2 && (
                    <button
                      onClick={() => removeText(i)}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      删除
                    </button>
                  )}
                </div>
                <input
                  type="text"
                  value={t.title}
                  onChange={(e) => updateText(i, "title", e.target.value)}
                  placeholder="课文标题"
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg mb-2 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                />
                <textarea
                  value={t.text}
                  onChange={(e) => updateText(i, "text", e.target.value)}
                  placeholder="粘贴课文内容..."
                  rows={4}
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                />
              </div>
            ))}
          </div>

          {error && (
            <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            onClick={handleCompare}
            disabled={loading}
            className="mt-4 w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                分析中...
              </span>
            ) : (
              "开始对比分析"
            )}
          </button>
        </div>

        {/* Results Section */}
        {result && (
          <>
            {/* Summary */}
            {result.summary.recommendation && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200 p-6 mb-6">
                <h3 className="text-sm font-semibold text-blue-800 mb-2">对比结论</h3>
                <div className="grid grid-cols-3 gap-4 mb-3">
                  <div className="text-center">
                    <div className="text-xs text-gray-500">等级范围</div>
                    <div className="text-lg font-bold text-blue-700">{result.summary.level_range}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">词数范围</div>
                    <div className="text-lg font-bold text-blue-700">{result.summary.word_count_range}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">可读性范围</div>
                    <div className="text-lg font-bold text-blue-700">{result.summary.readability_range}</div>
                  </div>
                </div>
                <p className="text-sm text-blue-900">{result.summary.recommendation}</p>
              </div>
            )}

            {/* Comparison Table */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="px-4 py-3 text-left font-semibold text-gray-600">指标</th>
                      {result.results.map((r, i) => (
                        <th key={i} className="px-4 py-3 text-center font-semibold text-gray-600">
                          {r.title || `课文${i + 1}`}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    <TableRow label="课文等级" values={result.results.map((r) => r.text_level || "-")} />
                    <TableRow label="语种" values={result.results.map((r) => r.language_name || "-")} />
                    <TableRow label="总词数" values={result.results.map((r) => r.metrics?.total_words?.toString() || "-")} />
                    <TableRow label="不重复词" values={result.results.map((r) => r.metrics?.unique_words?.toString() || "-")} />
                    <TableRow label="词汇丰富度" values={result.results.map((r) => r.metrics?.vocabulary_richness?.toFixed(3) || "-")} />
                    <TableRow label="学术词汇比" values={result.results.map((r) => r.metrics ? `${(r.metrics.awl_ratio * 100).toFixed(1)}%` : "-")} />
                    <TableRow label="平均句长" values={result.results.map((r) => r.metrics ? `${r.metrics.avg_sentence_length}词` : "-")} />
                    <TableRow label="可读性" values={result.results.map((r) => r.metrics?.flesch_reading_ease?.toFixed(1) || "-")} />
                    <TableRow label="长句数" values={result.results.map((r) => r.metrics?.long_sentences_count?.toString() || "-")} />
                    <TableRow label="连接词密度" values={result.results.map((r) => r.metrics ? `${r.metrics.connective_density}/百词` : "-")} />
                    <TableRow label="段落数" values={result.results.map((r) => r.metrics?.paragraph_count?.toString() || "-")} />
                    <TableRow label="体裁" values={result.results.map((r) => r.metrics?.genre_hint || "-")} />
                    <TableRow label="文本结构" values={result.results.map((r) => r.metrics?.text_structure || "-")} />
                    <TableRow label="难点词数" values={result.results.map((r) => r.difficult_words_count?.toString() || "-")} />
                  </tbody>
                </table>
              </div>
            </div>

            {/* Enhancement Tags Comparison */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {result.results.map((r, i) => (
                <div key={i} className="bg-white rounded-xl border border-gray-200 p-4">
                  <h4 className="text-sm font-semibold text-gray-800 mb-3">{r.title || `课文${i + 1}`}</h4>
                  {r.error ? (
                    <p className="text-sm text-red-500">{r.error}</p>
                  ) : (
                    <>
                      {r.cefr_distribution && (
                        <div className="mb-3">
                          <div className="text-xs text-gray-500 mb-1">CEFR 分布</div>
                          <div className="flex gap-1 h-4 rounded overflow-hidden">
                            {["A1-A2", "B1-B2", "C1-C2", "未分级"].map((level) => {
                              const total = r.metrics?.total_words || 1;
                              const count = r.cefr_distribution?.[level] || 0;
                              const pct = (count / total) * 100;
                              const colors: Record<string, string> = {
                                "A1-A2": "bg-green-400",
                                "B1-B2": "bg-blue-400",
                                "C1-C2": "bg-orange-400",
                                "未分级": "bg-gray-300",
                              };
                              return pct > 0 ? (
                                <div
                                  key={level}
                                  className={`${colors[level]} h-full`}
                                  style={{ width: `${pct}%` }}
                                  title={`${level}: ${count} (${pct.toFixed(1)}%)`}
                                />
                              ) : null;
                            })}
                          </div>
                        </div>
                      )}
                      {r.tag_labels && Object.keys(r.tag_labels).length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(r.tag_labels).map(([tag, label]) => (
                            <span key={tag} className="px-2 py-0.5 text-[10px] rounded-full bg-primary/10 text-primary">
                              {label}
                            </span>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function TableRow({ label, values }: { label: string; values: string[] }) {
  return (
    <tr>
      <td className="px-4 py-2 text-gray-500 font-medium">{label}</td>
      {values.map((v, i) => (
        <td key={i} className="px-4 py-2 text-center text-gray-800">{v}</td>
      ))}
    </tr>
  );
}
