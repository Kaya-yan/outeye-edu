"use client";

import React, { useState } from "react";

interface AnalysisResult {
  text_id: string;
  title: string;
  overall_difficulty: number;
  cefr_level: string;
  analysis_summary: string;
  teaching_suggestions: string[];
  lexical: {
    total_words: number;
    unique_words: number;
    vocabulary_richness: number;
    academic_word_count: number;
    academic_words: string[];
    unknown_words: string[];
    difficulty_score: number;
  };
  syntactic: {
    total_sentences: number;
    avg_sentence_length: number;
    sentence_types: Record<string, number>;
    complexity_score: number;
    flesch_kincaid_grade: number;
  };
  discourse: {
    coherence_score: number;
    genre_type: string;
    thematic_progression: string;
  };
  cognitive_load: {
    intrinsic_load: number;
    extraneous_load: number;
    germane_load: number;
    total_load: number;
    overload: boolean;
  };
}

interface LessonPlan {
  title: string;
  level: string;
  duration: number;
  objectives: Array<{
    description: string;
    bloom_level: string;
    assessment_method: string;
  }>;
  activities: Array<{
    name: string;
    description: string;
    duration: number;
    interaction_pattern: string;
  }>;
  formatted_plan: string;
}

export default function AnalysisPage() {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [studentLevel, setStudentLevel] = useState("B1");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null
  );
  const [lessonPlan, setLessonPlan] = useState<LessonPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"analysis" | "lesson">("analysis");

  const handleAnalyze = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/analysis/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          title,
          student_level: studentLevel,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setAnalysisResult(data);
      } else {
        const errData = await response.json().catch(() => ({}));
        setError(errData.detail || `分析失败 (${response.status})`);
      }
    } catch (error) {
      setError("网络错误，请检查后端服务是否运行");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateLessonPlan = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/analysis/generate-lesson-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          title,
          student_level: studentLevel,
          lesson_duration: 45,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setLessonPlan(data);
        setActiveTab("lesson");
      } else {
        const errData = await response.json().catch(() => ({}));
        setError(errData.detail || `教案生成失败 (${response.status})`);
      }
    } catch (error) {
      setError("网络错误，请检查后端服务是否运行");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">智能课文分析</h1>
          <p className="text-gray-600 mt-1">
            基于12大语言学理论的多维度课文分析
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 输入区域 */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold mb-4">课文输入</h2>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                课文标题
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="输入课文标题"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                学生水平
              </label>
              <select
                value={studentLevel}
                onChange={(e) => setStudentLevel(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="A1">A1 - 初级</option>
                <option value="A2">A2 - 基础</option>
                <option value="B1">B1 - 中级</option>
                <option value="B2">B2 - 中高级</option>
                <option value="C1">C1 - 高级</option>
                <option value="C2">C2 - 精通</option>
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                课文内容
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={12}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="粘贴课文内容..."
              />
            </div>

            <div className="flex space-x-4">
              <button
                onClick={handleAnalyze}
                disabled={loading || !text.trim()}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "分析中..." : "开始分析"}
              </button>
              <button
                onClick={handleGenerateLessonPlan}
                disabled={loading || !text.trim()}
                className="flex-1 bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                生成教案
              </button>
            </div>

            {error && (
              <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
                {error}
              </div>
            )}
          </div>

          {/* 结果展示区域 */}
          <div className="bg-white rounded-lg shadow-md p-6">
            {/* 标签页 */}
            <div className="flex border-b mb-4">
              <button
                className={`px-4 py-2 font-medium ${
                  activeTab === "analysis"
                    ? "text-blue-600 border-b-2 border-blue-600"
                    : "text-gray-500"
                }`}
                onClick={() => setActiveTab("analysis")}
              >
                分析结果
              </button>
              <button
                className={`px-4 py-2 font-medium ${
                  activeTab === "lesson"
                    ? "text-blue-600 border-b-2 border-blue-600"
                    : "text-gray-500"
                }`}
                onClick={() => setActiveTab("lesson")}
              >
                教案
              </button>
            </div>

            {/* 分析结果 */}
            {activeTab === "analysis" && analysisResult && (
              <div className="space-y-4">
                {/* 总体信息 */}
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-blue-900">总体评估</h3>
                  <div className="grid grid-cols-2 gap-4 mt-2">
                    <div>
                      <span className="text-sm text-gray-600">整体难度</span>
                      <p className="text-2xl font-bold text-blue-600">
                        {analysisResult.overall_difficulty}/10
                      </p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">CEFR等级</span>
                      <p className="text-2xl font-bold text-green-600">
                        {analysisResult.cefr_level}
                      </p>
                    </div>
                  </div>
                </div>

                {/* 分析摘要 */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-2">分析摘要</h3>
                  <p className="text-gray-700 whitespace-pre-line">
                    {analysisResult.analysis_summary}
                  </p>
                </div>

                {/* 词汇分析 */}
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">词汇分析</h3>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <span className="text-sm text-gray-600">总词数</span>
                      <p className="text-xl font-bold">
                        {analysisResult.lexical.total_words}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">词汇丰富度</span>
                      <p className="text-xl font-bold">
                        {(analysisResult.lexical.vocabulary_richness * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">学术词汇</span>
                      <p className="text-xl font-bold">
                        {analysisResult.lexical.academic_word_count}
                      </p>
                    </div>
                  </div>
                  {analysisResult.lexical.unknown_words.length > 0 && (
                    <div className="mt-3">
                      <span className="text-sm text-gray-600">生词：</span>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {analysisResult.lexical.unknown_words
                          .slice(0, 10)
                          .map((word, idx) => (
                            <span
                              key={idx}
                              className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-sm"
                            >
                              {word}
                            </span>
                          ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 认知负荷 */}
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">认知负荷</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">内在负荷</span>
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{
                            width: `${
                              (analysisResult.cognitive_load.intrinsic_load / 10) * 100
                            }%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {analysisResult.cognitive_load.intrinsic_load}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">外在负荷</span>
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-orange-500 h-2 rounded-full"
                          style={{
                            width: `${
                              (analysisResult.cognitive_load.extraneous_load / 10) * 100
                            }%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {analysisResult.cognitive_load.extraneous_load}
                      </span>
                    </div>
                    {analysisResult.cognitive_load.overload && (
                      <div className="bg-red-50 text-red-700 p-2 rounded text-sm">
                        ⚠️ 认知负荷过高，建议提供支架支持
                      </div>
                    )}
                  </div>
                </div>

                {/* 教学建议 */}
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">教学建议</h3>
                  <ul className="space-y-2">
                    {analysisResult.teaching_suggestions.map((suggestion, idx) => (
                      <li key={idx} className="flex items-start">
                        <span className="text-blue-500 mr-2">•</span>
                        <span className="text-gray-700">{suggestion}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* 教案 */}
            {activeTab === "lesson" && lessonPlan && (
              <div>
                <div className="bg-green-50 p-4 rounded-lg mb-4">
                  <h3 className="font-semibold text-green-900">
                    {lessonPlan.title}
                  </h3>
                  <p className="text-green-700">
                    水平：{lessonPlan.level} | 时长：{lessonPlan.duration}分钟
                  </p>
                </div>

                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 p-4 rounded-lg">
                    {lessonPlan.formatted_plan}
                  </pre>
                </div>
              </div>
            )}

            {/* 空状态 */}
            {!analysisResult && activeTab === "analysis" && (
              <div className="text-center text-gray-500 py-12">
                <p>输入课文内容并点击"开始分析"查看结果</p>
              </div>
            )}

            {!lessonPlan && activeTab === "lesson" && (
              <div className="text-center text-gray-500 py-12">
                <p>输入课文内容并点击"生成教案"查看结果</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
