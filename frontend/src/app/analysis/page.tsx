"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { apiPost } from "@/lib/api";
import dynamic from "next/dynamic";
import WhiteboxResults from "@/components/WhiteboxResults";
import TeachingPlanView from "@/components/TeachingPlanView";
import FileUploadZone from "@/components/FileUploadZone";
import TeachingContextPanel from "@/components/TeachingContextPanel";
import BlueprintOverview from "@/components/BlueprintOverview";
import { Blueprint, TeachingContext } from "@/lib/analysis";

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

interface TeachingPlan {
  difficulty_overview: string;
  teaching_suggestions: string[];
  activity_designs: Array<{
    name?: string;
    objective?: string;
    steps?: string;
    duration?: string;
    evidence?: { source_type: "wiki" | "rag"; title: string; relevance: number; content: string }[];
    degraded?: boolean;
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
  teaching_blueprint: Blueprint | null;
  teaching_plan: TeachingPlan;
  evidence_annotations: Record<string, unknown> | null;
  sources: Array<{ type: string; title?: string; score?: number }>;
  retrieval_info: { wiki_count: number; rag_count: number; retrieval_duration: number };
  generation_duration: number;
  total_duration: number;
  model: string;
}

type Step = "input" | "analysis" | "plan";

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
  const router = useRouter();
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
  const [planResult, setPlanResult] = useState<GeneratePlanResult | null>(null);
  const [showContextPanel, setShowContextPanel] = useState(false);

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

  // Step 2: Generate Teaching Plan（含双源检索，内部完成）
  const handleGenerate = async (context: TeachingContext) => {
    setError("");
    setLoading(true);
    setShowContextPanel(false);
    try {
      const result = await apiPost<GeneratePlanResult>("/analysis/generate-plan", {
        text,
        title,
        student_level: context.studentLevel,
        language: language || undefined,
        native_language: nativeLanguage || undefined,
        course_type: context.courseType || undefined,
        class_size: context.classSize || undefined,
        duration_minutes: context.durationMinutes,
        mode: context.mode,
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
    setPlanResult(null);
    setShowContextPanel(false);
    setError("");
  };

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="brand-surface px-6 py-7 sm:px-8 sm:py-8 mb-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="section-title mb-2">Academic Analysis Workbench</div>
              <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-ink-900">课文智能分析</h1>
              <p className="text-sm sm:text-base text-ink-500 mt-3 max-w-2xl leading-7">
                在柔和、克制的工作台中完成课文输入、白盒分析、双源检索与教学方案生成，并把结果自然推进到 HTML 课件编辑与课堂展示链路。
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3 sm:gap-4 lg:w-[360px]">
              <div className="data-card p-4 text-center bg-white/90">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">CEFR</div>
                <div className="mt-2 text-lg font-semibold text-ink-900">A1-C2</div>
              </div>
              <div className="data-card p-4 text-center bg-white/90">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Dual</div>
                <div className="mt-2 text-lg font-semibold text-ink-900">Wiki + RAG</div>
              </div>
              <div className="data-card p-4 text-center bg-white/90">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Flow</div>
                <div className="mt-2 text-lg font-semibold text-ink-900">Plan → Courseware</div>
              </div>
            </div>
          </div>
        </div>

        {/* Stepper */}
        <div className="page-surface-strong px-4 py-4 sm:px-6 mb-4">
          <Stepper current={step} />
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
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
              onNext={() => setShowContextPanel(true)}
              onBack={() => setStep("input")}
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

      {/* Teaching Context Panel Modal */}
      {showContextPanel && (
        <TeachingContextPanel
          initialStudentLevel={studentLevel}
          onConfirm={handleGenerate}
          onCancel={() => setShowContextPanel(false)}
          loading={loading}
        />
      )}
    </div>
  );
}

// ============ Stepper ============

function Stepper({ current }: { current: Step }) {
  const steps: { key: Step; label: string; icon: string; hint: string }[] = [
    { key: "input", label: "输入课文", icon: "📝", hint: "准备文本" },
    { key: "analysis", label: "白盒分析", icon: "📊", hint: "形成判断" },
    { key: "plan", label: "教学方案", icon: "📋", hint: "进入课件" },
  ];
  const currentIdx = steps.findIndex((s) => s.key === current);

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {steps.map((s, i) => {
        const isCurrent = i === currentIdx;
        const isDone = i < currentIdx;
        return (
          <div
            key={s.key}
            className={`rounded-2xl border px-4 py-3 transition-colors ${
              isCurrent
                ? "bg-primary-100 border-primary-300 shadow-soft"
                : isDone
                  ? "bg-sage-100 border-sage-200"
                  : "bg-canvas-100/80 border-black/5"
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                  isCurrent ? "bg-white text-ink-900" : isDone ? "bg-white text-ink-800" : "bg-white/80 text-ink-500"
                }`}>
                  {isDone ? "✓" : s.icon}
                </span>
                <div>
                  <div className={`text-sm font-semibold ${isCurrent || isDone ? "text-ink-900" : "text-ink-600"}`}>{s.label}</div>
                  <div className={`text-xs ${isCurrent ? "text-ink-600" : isDone ? "text-ink-500" : "text-ink-400"}`}>{s.hint}</div>
                </div>
              </div>
              <span className={`text-[10px] uppercase tracking-[0.16em] ${
                isCurrent ? "text-ink-700" : isDone ? "text-ink-500" : "text-ink-400"
              }`}>
                {isCurrent ? "进行中" : isDone ? "完成" : `Step ${i + 1}`}
              </span>
            </div>
          </div>
        );
      })}
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
      <div className="workbench-panel space-y-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="section-title mb-2">Step 1</div>
            <h2 className="text-2xl font-semibold text-ink-900">输入课文</h2>
            <p className="text-sm text-ink-500 mt-2">支持上传、OCR 与手动输入。完成后即可进入白盒分析。</p>
          </div>
          <div className="rounded-full bg-canvas-200 px-4 py-2 text-xs font-medium text-ink-600 shadow-soft">
            当前字数：{wordCount}
          </div>
        </div>

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
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none"
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
                    ? "bg-primary-600 text-white border-primary-600"
                    : "bg-white text-gray-600 border-gray-300 hover:border-primary-500/50"
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
            className="px-4 py-2 border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none text-sm"
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
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none"
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
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none"
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
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none"
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
          className="w-full py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
  onNext,
  onBack,
}: {
  analysis: WhiteboxAnalysis;
  loading: boolean;
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="workbench-panel space-y-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="section-title mb-2">Step 2</div>
            <h2 className="text-2xl font-semibold text-ink-900">白盒分析结果</h2>
          </div>
          <div className="rounded-full bg-canvas-200 px-4 py-2 text-xs font-medium text-ink-600 shadow-soft">
            耗时 {analysis.analysis_duration}s
          </div>
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
          onClick={onNext}
          disabled={loading}
          className="flex-1 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "处理中..." : "下一步：生成教学设计"}
        </button>
      </div>
    </div>
  );
}

// ============ Step 3: Plan ============

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
  const router = useRouter();
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [revising, setRevising] = useState(false);
  const [revisionError, setRevisionError] = useState("");
  const [creatingCourseware, setCreatingCourseware] = useState(false);
  const [blueprintConfirmed, setBlueprintConfirmed] = useState(false);

  const handleCreateCourseware = async () => {
    setCreatingCourseware(true);
    try {
      const resp = await apiPost<{ project: { id: string } }>("/courseware/from-plan", {
        title: result.text_title || "教学课件",
        source_plan_id: undefined,
        mode: "slides",
        template_id: "classroom_default",
        plan: result.teaching_plan,
        learner_gap: result.learner_gap,
        enhancement_tags: result.enhancement_tags,
      });
      router.push(`/courseware/${resp.project.id}/edit`);
    } catch (e: unknown) {
      setRevisionError(e instanceof Error ? e.message : "创建课件失败，请重试");
    } finally {
      setCreatingCourseware(false);
    }
  };

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
        `/api/v1/analysis/export`,
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
      <div className="workbench-panel">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-5">
          <div>
            <div className="section-title mb-2">Step 3</div>
            <h2 className="text-2xl font-semibold text-ink-900">教学方案</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-canvas-200 px-3 py-1.5 text-ink-600 shadow-soft">{result.text_level} → {result.student_level}</span>
            <span className="rounded-full bg-sage-100 px-3 py-1.5 text-ink-700 shadow-soft">总耗时 {result.total_duration}s</span>
          </div>
        </div>

        <div className="archive-surface p-4 mb-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="section-title mb-2">Ready for Courseware</div>
              <p className="text-sm text-ink-600 leading-6">
                教学方案已经完成。你可以继续导出传统格式，也可以直接把它推进到教学课件工作台，进入可编辑、可展示、可沉淀组件的下一阶段。
              </p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-ink-500">
              <span className="drawer-handle bg-white border border-black/5 text-ink-500">保留 PPT / Word / HTML 导出</span>
              <span className="drawer-handle bg-sage-100 border border-sage-200 text-ink-600">生成后自动进入编辑器</span>
            </div>
          </div>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {result.enhancement_tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs rounded-full bg-primary-100 text-primary-700"
            >
              {result.tag_labels?.[tag] || tag.replace(/_/g, " ")}
            </span>
          ))}
        </div>

        {result.teaching_blueprint && !blueprintConfirmed ? (
          <BlueprintOverview
            blueprint={result.teaching_blueprint}
            onConfirm={() => setBlueprintConfirmed(true)}
          />
        ) : (
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
        )}

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

      {/* Courseware entry */}
      <div className="archive-surface p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="w-11 h-11 rounded-2xl bg-canvas-300 flex items-center justify-center text-ink-700 shadow-soft">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <div className="flex-1 max-w-2xl">
              <div className="section-title mb-2">Courseware</div>
              <h3 className="text-lg font-semibold text-ink-900">把教学方案推进到课件工作台</h3>
              <p className="text-sm text-ink-500 mt-1 leading-6">
                当前这份方案已经具备进入课件生产链路的条件。生成后会自动创建课件项目，并直接进入编辑器继续工作。
              </p>
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:w-[360px]">
            <button
              onClick={handleCreateCourseware}
              disabled={creatingCourseware}
              className="btn-primary w-full rounded-xl py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creatingCourseware ? "生成中..." : "生成教学课件"}
            </button>
            <button
              onClick={() => router.push('/courseware')}
              className="btn-secondary w-full rounded-xl py-3"
            >
              查看课件工作台
            </button>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="data-card p-4 bg-white/90">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Create</div>
            <div className="mt-2 text-sm font-semibold text-ink-900">创建课件项目</div>
            <p className="mt-1 text-xs text-ink-500 leading-5">用当前教学方案建立可继续编辑的 HTML 课件。</p>
          </div>
          <div className="data-card p-4 bg-white/90">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Edit</div>
            <div className="mt-2 text-sm font-semibold text-ink-900">进入编辑器</div>
            <p className="mt-1 text-xs text-ink-500 leading-5">生成后自动跳转到编辑器，继续做页面与组件调整。</p>
          </div>
          <div className="data-card p-4 bg-white/90">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Present</div>
            <div className="mt-2 text-sm font-semibold text-ink-900">进入展示终态</div>
            <p className="mt-1 text-xs text-ink-500 leading-5">在课件项目内继续进入课堂展示模式，完成完整演示链。</p>
          </div>
        </div>
      </div>

      <button
        onClick={onReset}
        className="btn-secondary w-full rounded-xl py-3"
      >
        分析新课文
      </button>
    </div>
  );
}
