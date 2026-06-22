"use client";

import React, { useState } from "react";
import { apiPost } from "@/lib/api";
import dynamic from "next/dynamic";
import WhiteboxResults from "@/components/WhiteboxResults";
import TeachingPlanView from "@/components/TeachingPlanView";
import FileUploadZone from "@/components/FileUploadZone";

const TiptapEditor = dynamic(() => import("@/components/TiptapEditor"), {
  ssr: false,
  loading: () => (
    <div className="border border-gray-300 rounded-lg bg-white min-h-[200px] flex items-center justify-center text-gray-400">
      加载编辑器...
    </div>
  ),
});

// ============ Types ============

interface WhiteboxAnalysis {
  text_id: string;
  title: string;
  text_level: string;
  language: string;
  language_name: string;
  vocabulary: {
    total_words: number;
    unique_words: number;
    cefr_distribution: Record<string, number>;
    awl_count: number;
    awl_ratio: number;
    difficult_words: Array<{ word: string; level: string; count: number; in_awl: boolean }>;
    vocabulary_richness: number;
  };
  syntax: {
    total_sentences: number;
    avg_sentence_length: number;
    max_sentence: { preview: string; word_count: number; index: number };
    long_sentences_count: number;
    very_long_sentences_count: number;
    flesch_reading_ease: number;
  };
  discourse: {
    paragraph_count: number;
    connective_density: number;
    genre_hint: string;
    text_structure?: string;
    teaching_points?: string[];
  };
  learner_gap: {
    text_level: string;
    student_level: string;
    gap: string;
    gap_description: string;
  };
  enhancement_tags: string[];
  tag_labels?: Record<string, string>;
  teaching_insights?: Array<{
    metric_name: string;
    metric_value: string;
    teaching_implication: string;
    suggested_action: string;
    confidence: string;
  }>;
  cultural_elements?: Array<{
    category: string;
    keyword: string;
    context: string;
    explanation: string;
  }>;
  tag_details: Record<string, unknown>;
  wiki_tags: string[];
  rag_tags: string[];
  teaching_tips: string[];
  analysis_duration: number;
}

interface RetrievalResult {
  wiki_results: Array<{
    page_name: string;
    title: string;
    summary: string;
    relevance_score: number;
    match_type: string;
    tags: string[];
  }>;
  rag_results: Array<{
    chunk_id: string;
    content: string;
    score: number;
    metadata: Record<string, unknown>;
  }>;
  wiki_count: number;
  rag_count: number;
  retrieval_duration: number;
}

interface TeachingPlan {
  difficulty_overview: string;
  teaching_suggestions: string[];
  activity_designs: Array<{
    name?: string;
    objective?: string;
    steps?: string;
    duration?: string;
  }>;
  differentiation: string;
  theoretical_basis: string;
}

interface GeneratePlanResult {
  text_title: string;
  text_level: string;
  student_level: string;
  learner_gap: { gap: string; gap_description: string };
  enhancement_tags: string[];
  tag_labels?: Record<string, string>;
  teaching_plan: TeachingPlan;
  sources: Array<{ type: string; title?: string; score?: number }>;
  retrieval_info: { wiki_count: number; rag_count: number; retrieval_duration: number };
  generation_duration: number;
  total_duration: number;
  model: string;
}

type Step = "input" | "analysis" | "retrieval" | "plan";

const CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];

const LANGUAGES = [
  { code: "", label: "自动检测" },
  { code: "en", label: "英语 English" },
  { code: "ja", label: "日语 日本語" },
  { code: "fr", label: "法语 Français" },
  { code: "de", label: "德语 Deutsch" },
  { code: "es", label: "西班牙语 Español" },
  { code: "ko", label: "韩语 한국어" },
];

// ============ Page ============

export default function AnalysisPage() {
  const [step, setStep] = useState<Step>("input");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [studentLevel, setStudentLevel] = useState("B1");
  const [language, setLanguage] = useState("");
  const [nativeLanguage, setNativeLanguage] = useState("");
  const [courseType, setCourseType] = useState("");
  const [classSize, setClassSize] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [analysis, setAnalysis] = useState<WhiteboxAnalysis | null>(null);
  const [retrieval, setRetrieval] = useState<RetrievalResult | null>(null);
  const [planResult, setPlanResult] = useState<GeneratePlanResult | null>(null);

  // 统计词数：英文按空格分词，中文按字符计数（1个汉字≈1.5词）
  const wordCount = (() => {
    const cleaned = text.replace(/<[^>]*>/g, "").trim();
    if (!cleaned) return 0;
    const englishWords = cleaned.split(/\s+/).filter(Boolean).length;
    const chineseChars = (cleaned.match(/[一-鿿]/g) || []).length;
    return englishWords + Math.ceil(chineseChars * 0.67);
  })();

  // Step 1: Whitebox Analysis
  const handleAnalyze = async () => {
    if (wordCount < 20) {
      setError("课文内容太短，至少需要20个词");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const result = await apiPost<WhiteboxAnalysis>("/analysis/whitebox", {
        text,
        title,
        student_level: studentLevel,
        language: language || undefined,
        native_language: nativeLanguage || undefined,
        course_type: courseType || undefined,
        class_size: classSize ? parseInt(classSize) : undefined,
      });
      setAnalysis(result);
      setStep("analysis");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "分析失败");
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Dual Retrieval
  const handleRetrieve = async () => {
    if (!analysis) return;
    setError("");
    setLoading(true);
    try {
      const result = await apiPost<RetrievalResult>("/analysis/retrieve", {
        wiki_tags: analysis.wiki_tags,
        rag_tags: analysis.rag_tags,
        enhancement_tags: analysis.enhancement_tags,
        text_title: title,
        max_results: 3,
      });
      setRetrieval(result);
      setStep("retrieval");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "检索失败");
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Generate Teaching Plan
  const handleGenerate = async () => {
    setError("");
    setLoading(true);
    try {
      const result = await apiPost<GeneratePlanResult>("/analysis/generate-plan", {
        text,
        title,
        student_level: studentLevel,
        language: language || undefined,
        native_language: nativeLanguage || undefined,
        course_type: courseType || undefined,
        class_size: classSize ? parseInt(classSize) : undefined,
        max_retrieval_results: 3,
      });
      setPlanResult(result);
      setStep("plan");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  };

  // Reset
  const handleReset = () => {
    setStep("input");
    setAnalysis(null);
    setRetrieval(null);
    setPlanResult(null);
    setError("");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">课文智能分析</h1>
          <p className="text-sm text-gray-500 mt-1">
            ADDSR-Lite: 白盒分析 → 双源检索 → 融合生成
          </p>
        </div>

        {/* Stepper */}
        <Stepper current={step} />

        {/* Error */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Step Content */}
        <div className="mt-6">
          {step === "input" && (
            <InputStep
              title={title}
              setTitle={setTitle}
              text={text}
              setText={setText}
              studentLevel={studentLevel}
              setStudentLevel={setStudentLevel}
              language={language}
              setLanguage={setLanguage}
              nativeLanguage={nativeLanguage}
              setNativeLanguage={setNativeLanguage}
              courseType={courseType}
              setCourseType={setCourseType}
              classSize={classSize}
              setClassSize={setClassSize}
              wordCount={wordCount}
              loading={loading}
              onAnalyze={handleAnalyze}
            />
          )}

          {step === "analysis" && analysis && (
            <AnalysisStep
              analysis={analysis}
              loading={loading}
              onRetrieve={handleRetrieve}
              onBack={() => setStep("input")}
            />
          )}

          {step === "retrieval" && analysis && retrieval && (
            <RetrievalStep
              analysis={analysis}
              retrieval={retrieval}
              loading={loading}
              onGenerate={handleGenerate}
              onBack={() => setStep("analysis")}
            />
          )}

          {step === "plan" && planResult && (
            <PlanStep
              result={planResult}
              onReset={handleReset}
              onUpdate={setPlanResult}
              text={text}
              title={title}
              studentLevel={studentLevel}
              language={language}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ============ Stepper ============

function Stepper({ current }: { current: Step }) {
  const steps: { key: Step; label: string; icon: string }[] = [
    { key: "input", label: "输入课文", icon: "📝" },
    { key: "analysis", label: "白盒分析", icon: "📊" },
    { key: "retrieval", label: "双源检索", icon: "🔍" },
    { key: "plan", label: "教学方案", icon: "📋" },
  ];
  const currentIdx = steps.findIndex((s) => s.key === current);

  return (
    <div className="flex items-center gap-2">
      {steps.map((s, i) => (
        <React.Fragment key={s.key}>
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              i === currentIdx
                ? "bg-primary text-white"
                : i < currentIdx
                ? "bg-green-100 text-green-800"
                : "bg-gray-100 text-gray-400"
            }`}
          >
            <span>{i < currentIdx ? "✓" : s.icon}</span>
            {s.label}
          </div>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-px ${i < currentIdx ? "bg-green-300" : "bg-gray-200"}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ============ Step 1: Input ============

function InputStep({
  title,
  setTitle,
  text,
  setText,
  studentLevel,
  setStudentLevel,
  language,
  setLanguage,
  nativeLanguage,
  setNativeLanguage,
  courseType,
  setCourseType,
  classSize,
  setClassSize,
  wordCount,
  loading,
  onAnalyze,
}: {
  title: string;
  setTitle: (v: string) => void;
  text: string;
  setText: (v: string) => void;
  studentLevel: string;
  setStudentLevel: (v: string) => void;
  language: string;
  setLanguage: (v: string) => void;
  nativeLanguage: string;
  setNativeLanguage: (v: string) => void;
  courseType: string;
  setCourseType: (v: string) => void;
  classSize: string;
  setClassSize: (v: string) => void;
  wordCount: number;
  loading: boolean;
  onAnalyze: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">输入课文</h2>

        {/* File Upload */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">上传文件</label>
          <FileUploadZone
            onTextExtracted={(extractedText) => setText(extractedText)}
            onFilename={(filename) => {
              if (!title) setTitle(filename.replace(/\.[^.]+$/, ""));
            }}
          />
        </div>

        <div className="flex items-center gap-2 my-4">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-xs text-gray-400">或手动输入</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>

        {/* Title */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">课文标题</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例：Language Learning Evolution"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
          />
        </div>

        {/* Student Level */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">学生水平</label>
          <div className="flex gap-2">
            {CEFR_LEVELS.map((level) => (
              <button
                key={level}
                onClick={() => setStudentLevel(level)}
                className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                  studentLevel === level
                    ? "bg-primary text-white border-primary"
                    : "bg-white text-gray-600 border-gray-300 hover:border-primary/50"
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        {/* Language */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">课文语种</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none text-sm"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>{lang.label}</option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-1">默认自动检测，也可手动指定</p>
        </div>

        {/* Student Profile - Collapsible */}
        <details className="mb-4 group">
          <summary className="text-sm font-medium text-gray-600 cursor-pointer hover:text-gray-800 flex items-center gap-1">
            <svg className="w-4 h-4 transition-transform group-open:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
            学生画像（可选，提升教案针对性）
          </summary>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-4 pl-5">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">学生母语</label>
              <select
                value={nativeLanguage}
                onChange={(e) => setNativeLanguage(e.target.value)}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
              >
                <option value="">未指定</option>
                <option value="zh">中文</option>
                <option value="ja">日语</option>
                <option value="ko">韩语</option>
                <option value="ar">阿拉伯语</option>
                <option value="ru">俄语</option>
                <option value="pt">葡萄牙语</option>
                <option value="other">其他</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">课程类型</label>
              <select
                value={courseType}
                onChange={(e) => setCourseType(e.target.value)}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
              >
                <option value="">未指定</option>
                <option value="精读">精读</option>
                <option value="泛读">泛读</option>
                <option value="听说">听说</option>
                <option value="写作">写作</option>
                <option value="综合">综合</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">班级人数</label>
              <input
                type="number"
                value={classSize}
                onChange={(e) => setClassSize(e.target.value)}
                placeholder="例：30"
                min={1}
                max={200}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
              />
            </div>
          </div>
        </details>

        {/* Text Editor */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            课文内容
            <span className="ml-2 text-gray-400 font-normal">({wordCount} 词)</span>
          </label>
          <TiptapEditor content={text} onChange={setText} />
        </div>

        {/* Submit */}
        <button
          onClick={onAnalyze}
          disabled={loading || wordCount < 20}
          className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              分析中...
            </span>
          ) : (
            "开始白盒分析"
          )}
        </button>
      </div>
    </div>
  );
}

// ============ Step 2: Analysis ============

function AnalysisStep({
  analysis,
  loading,
  onRetrieve,
  onBack,
}: {
  analysis: WhiteboxAnalysis;
  loading: boolean;
  onRetrieve: () => void;
  onBack: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">白盒分析结果</h2>
          <span className="text-xs text-gray-400">耗时 {analysis.analysis_duration}s</span>
        </div>
        <WhiteboxResults data={analysis} />
      </div>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="px-6 py-2.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
        >
          返回修改
        </button>
        <button
          onClick={onRetrieve}
          disabled={loading}
          className="flex-1 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? "检索中..." : "下一步：双源检索"}
        </button>
      </div>
    </div>
  );
}

// ============ Step 3: Retrieval ============

function RetrievalStep({
  analysis,
  retrieval,
  loading,
  onGenerate,
  onBack,
}: {
  analysis: WhiteboxAnalysis;
  retrieval: RetrievalResult;
  loading: boolean;
  onGenerate: () => void;
  onBack: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">双源检索结果</h2>
          <span className="text-xs text-gray-400">耗时 {retrieval.retrieval_duration}s</span>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-blue-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-700">{retrieval.wiki_count}</div>
            <div className="text-xs text-blue-600">Wiki 理论</div>
          </div>
          <div className="bg-green-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-700">{retrieval.rag_count}</div>
            <div className="text-xs text-green-600">RAG 资源</div>
          </div>
        </div>

        {/* Wiki Results */}
        {retrieval.wiki_results.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">📖 Wiki 教学理论</h3>
            <div className="space-y-2">
              {retrieval.wiki_results.map((r, i) => (
                <div key={i} className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-blue-800">{r.title}</span>
                    <span className="text-xs text-blue-500">相关度 {(r.relevance_score * 100).toFixed(0)}%</span>
                  </div>
                  {r.summary && <p className="text-xs text-blue-600 mt-1 line-clamp-2">{r.summary}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* RAG Results */}
        {retrieval.rag_results.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">📄 教学资源</h3>
            <div className="space-y-2">
              {retrieval.rag_results.map((r, i) => (
                <div key={i} className="p-3 bg-green-50 rounded-lg border border-green-100">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-green-800">
                      {(r.metadata as { title?: string })?.title || `文档 ${i + 1}`}
                    </span>
                    <span className="text-xs text-green-500">相关度 {(r.score * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-xs text-green-600 line-clamp-2">{r.content}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {retrieval.wiki_count === 0 && retrieval.rag_count === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            未检索到相关资源，将基于分析指标直接生成教学方案
          </p>
        )}
      </div>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="px-6 py-2.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
        >
          返回分析
        </button>
        <button
          onClick={onGenerate}
          disabled={loading}
          className="flex-1 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              AI 生成中...
            </span>
          ) : (
            "生成教学方案"
          )}
        </button>
      </div>
    </div>
  );
}

// ============ Step 4: Plan ============

function PlanStep({
  result,
  onReset,
  onUpdate,
  text,
  title,
  studentLevel,
  language,
}: {
  result: GeneratePlanResult;
  onReset: () => void;
  onUpdate?: (r: GeneratePlanResult) => void;
  text?: string;
  title?: string;
  studentLevel?: string;
  language?: string;
}) {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [revising, setRevising] = useState(false);
  const [revisionError, setRevisionError] = useState("");

  const handleRevise = async (instruction: string, section?: string) => {
    if (!text) return;
    setRevising(true);
    setRevisionError("");
    try {
      const resp = await apiPost<{
        teaching_plan: GeneratePlanResult["teaching_plan"];
        revision_note: string;
        generation_duration: number;
        model: string;
      }>("/analysis/revise-plan", {
        original_plan: result.teaching_plan,
        revision_instruction: instruction,
        text,
        title: title || "",
        student_level: studentLevel || "B1",
        language: language || undefined,
        section_to_revise: section || undefined,
      });

      if (onUpdate) {
        onUpdate({
          ...result,
          teaching_plan: resp.teaching_plan,
          generation_duration: resp.generation_duration,
          model: resp.model,
        });
      }
    } catch (e) {
      setRevisionError(e instanceof Error ? e.message : "修订失败，请稍后重试");
    } finally {
      setRevising(false);
    }
  };

  const handleExport = async (format: "pptx" | "docx" | "html") => {
    setExporting(true);
    setExportError("");
    try {
      const token = localStorage.getItem("token");

      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/analysis/export`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            plan: {
              ...result.teaching_plan,
              learner_gap: result.learner_gap,
            },
            format,
            title: result.text_title || "教学方案",
          }),
        }
      );

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || "导出失败");
      }

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `教学方案.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "导出失败");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">教学方案</h2>
          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span>{result.text_level} → {result.student_level}</span>
            <span>总耗时 {result.total_duration}s</span>
          </div>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {result.enhancement_tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs rounded-full bg-primary/10 text-primary"
            >
              {result.tag_labels?.[tag] || tag.replace(/_/g, " ")}
            </span>
          ))}
        </div>

        <TeachingPlanView
          plan={result.teaching_plan}
          sources={result.sources}
          model={result.model}
          duration={result.generation_duration}
          onExport={handleExport}
          exporting={exporting}
          onRevise={handleRevise}
          revising={revising}
          text={text}
          title={title}
          studentLevel={studentLevel}
          language={language}
        />

        {exportError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {exportError}
          </div>
        )}
        {revisionError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {revisionError}
          </div>
        )}
      </div>

      <button
        onClick={onReset}
        className="w-full py-2.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
      >
        分析新课文
      </button>
    </div>
  );
}
