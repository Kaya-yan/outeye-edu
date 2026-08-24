"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPost, apiRequest } from "@/lib/api";
import dynamic from "next/dynamic";
import WhiteboxResults from "@/components/WhiteboxResults";
import TeachingPlanView from "@/components/TeachingPlanView";
import FileUploadZone from "@/components/FileUploadZone";
import BlueprintOverview from "@/components/BlueprintOverview";
import PlanEvaluationForm from "@/components/PlanEvaluationForm";
import { Blueprint, TeachingContext } from "@/lib/analysis";
import { CEFR_LEVELS, cefrLabel } from "@/lib/cefr";

const TiptapEditor = dynamic(() => import("@/components/TiptapEditor"), {
  ssr: false,
  loading: () => (
    <div className="min-h-[240px] flex items-center justify-center text-sm text-ink-400">
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
  framework?: string;
  objectives?: Array<{ text: string; bloom?: string; assessment?: string }>;
  difficulty_overview: string;
  teaching_suggestions: string[];
  activity_designs: Array<{
    name?: string;
    objective?: string;
    steps?: string;
    duration?: string;
    assessment?: string;
    evidence?: { source_type: "wiki" | "rag"; title: string; relevance: number; content: string }[];
    degraded?: boolean;
  }>;
  assessment?: { formative?: string[]; summative?: string[] };
  differentiation: string;
  theoretical_basis: string;
  self_check?: Record<string, unknown>;
}

interface DifficultWord {
  word: string;
  level: string;
  count: number;
  in_awl: boolean;
}

interface CulturalElement {
  category: string;
  keyword: string;
  context: string;
  explanation: string;
}

interface GeneratePlanResult {
  text_title: string;
  text_level: string;
  language_name?: string;
  student_level: string;
  learner_gap: { gap: string; gap_description: string };
  vocabulary?: {
    total_words: number;
    unique_words: number;
    cefr_distribution: Record<string, number>;
    awl_count: number;
    awl_ratio: number;
    difficult_words: DifficultWord[];
    vocabulary_richness: number;
  };
  cultural_elements?: CulturalElement[];
  enhancement_tags: string[];
  tag_labels?: Record<string, string>;
  teaching_blueprint: Blueprint | null;
  teaching_plan: TeachingPlan;
  evidence_annotations: Record<string, unknown> | null;
  sources: Array<{ type: string; title?: string; score?: number }>;
  retrieval_info: { wiki_count: number; rag_count: number; retrieval_duration: number };
  syntax?: {
    avg_sentence_length: number;
    max_sentence?: { preview: string; word_count: number; index: number };
    long_sentences_count: number;
    flesch_reading_ease: number;
  };
  discourse?: { paragraph_count: number; connective_density: number; genre_hint: string };
  generation_settings?: {
    duration_minutes: number;
    course_type?: string;
    class_size?: number;
    native_language?: string;
  };
  generation_duration: number;
  total_duration: number;
  model: string;
  prompt_version?: string;
  fallback?: boolean;
}

type Step = "input" | "analysis" | "plan";

const COURSE_TYPES = ["精读", "泛读", "听说", "读写", "翻译", "写作", "综合"];

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
  const [durationInput, setDurationInput] = useState("90");
  const [planMode, setPlanMode] = useState<"basic" | "enhanced">("enhanced");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [analysis, setAnalysis] = useState<WhiteboxAnalysis | null>(null);
  const [cultureStatus, setCultureStatus] = useState<"idle" | "loading" | "enriched" | "fallback">("idle");
  const [versions, setVersions] = useState<{ basic?: GeneratePlanResult; enhanced?: GeneratePlanResult }>({});
  const [activeVersion, setActiveVersion] = useState<"basic" | "enhanced">("enhanced");
  const [lastContext, setLastContext] = useState<TeachingContext | null>(null);

  // 从历史记录点"继续"进入：恢复上次的课文与设置；
  // 已完成过分析的记录自动重析（白盒为确定性计算，秒级），直接回到结果视图
  const [autoAnalyzeQueued, setAutoAnalyzeQueued] = useState(false);
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("outeye:resume-project");
      if (!raw) return;
      sessionStorage.removeItem("outeye:resume-project");
      const p = JSON.parse(raw) as {
        title?: string;
        source_text?: string;
        student_level?: string;
        course_type?: string;
        duration_minutes?: number;
        auto_analyze?: boolean;
      };
      if (p.title) setTitle(p.title);
      if (p.source_text) setText(p.source_text);
      if (p.student_level) setStudentLevel(p.student_level);
      if (p.course_type) setCourseType(p.course_type);
      if (p.duration_minutes) setDurationInput(String(p.duration_minutes));
      if (p.auto_analyze && p.source_text) setAutoAnalyzeQueued(true);
    } catch {
      // 恢复失败不阻塞正常使用
    }
  }, []);

  // 结果出来后自动平滑滚回页面顶部，避免用户拖动半天
  // 用 prevRef 记录上一次的"是否有结果"，只在 null→有值 的转换瞬间触发，避免用户滚动后再被弹回
  const prevHadResultRef = useRef(false);
  useEffect(() => {
    const hasResult = analysis !== null || versions.basic !== undefined || versions.enhanced !== undefined;
    if (hasResult && !prevHadResultRef.current) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
    prevHadResultRef.current = hasResult;
  }, [analysis, versions]);

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
        duration_minutes: parseInt(durationInput, 10) || undefined,
      });
      setAnalysis(result);
      setStep("analysis");
      void enrichCulture(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "分析失败");
    } finally {
      setLoading(false);
    }
  };

  // 文化背景渐进式具体化：白盒秒回后由 LLM 异步替换通用建议为具体事实，不阻塞主流程
  const enrichCulture = async (result: WhiteboxAnalysis) => {
    if (!result.cultural_elements?.length) return;
    setCultureStatus("loading");
    try {
      const enriched = await apiPost<{
        cultural_elements: CulturalElement[];
        fallback: boolean;
      }>("/analysis/culture-enrich", {
        text,
        language_name: result.language_name,
        cultural_elements: result.cultural_elements,
      });
      setCultureStatus(enriched.fallback ? "fallback" : "enriched");
      if (enriched.cultural_elements?.length) {
        setAnalysis((prev) =>
          prev && prev.text_id === result.text_id
            ? { ...prev, cultural_elements: enriched.cultural_elements }
            : prev
        );
      }
    } catch {
      setCultureStatus("fallback");
    }
  };

  // 结果页"生成教案前确认"里改学生水平：白盒是确定性秒级计算，静默重算保持难度差距口径一致
  // 已富化的文化背景保留，不重复触发 LLM
  const [recomputing, setRecomputing] = useState(false);
  const handleStudentLevelChange = async (level: string) => {
    if (level === studentLevel) return;
    setStudentLevel(level);
    if (!text) return;
    setRecomputing(true);
    try {
      const result = await apiPost<WhiteboxAnalysis>("/analysis/whitebox", {
        text,
        title,
        student_level: level,
        language: language || undefined,
        native_language: nativeLanguage || undefined,
        course_type: courseType || undefined,
        class_size: classSize ? parseInt(classSize) : undefined,
        duration_minutes: parseInt(durationInput, 10) || undefined,
      });
      setAnalysis((prev) =>
        prev ? { ...result, cultural_elements: prev.cultural_elements } : result
      );
    } catch {
      // 重算失败保留原分析；生成教案时仍使用新水平
    } finally {
      setRecomputing(false);
    }
  };

  // 历史恢复后的一次性自动分析（在上方恢复 useEffect 写入状态之后触发）
  useEffect(() => {
    if (!autoAnalyzeQueued) return;
    setAutoAnalyzeQueued(false);
    void handleAnalyze();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoAnalyzeQueued]);

  // Step 2: Generate Teaching Plan（含双源检索，内部完成）
  const generateVersion = async (context: TeachingContext, mode: "basic" | "enhanced") => {
    setError("");
    setLoading(true);
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
        mode,
        max_retrieval_results: 3,
      });
      setVersions((prev) => ({ ...prev, [mode]: result }));
      setActiveVersion(mode);
      setStep("plan");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  };

  // 分析完成后，直接用首屏"教学设置"里的值生成教案
  const handleGenerateFromSettings = async () => {
    const n = parseInt(durationInput, 10);
    const size = classSize ? parseInt(classSize, 10) : 30;
    const context: TeachingContext = {
      courseType: courseType || "精读",
      durationMinutes: Math.min(180, Math.max(5, Number.isNaN(n) ? 90 : n)),
      classSize: Number.isNaN(size) ? 30 : size,
      studentLevel,
      mode: planMode,
    };
    setLastContext(context);
    await generateVersion(context, context.mode);
  };

  const handleGenerateOther = async () => {
    if (!lastContext) return;
    const other = activeVersion === "basic" ? "enhanced" : "basic";
    await generateVersion(lastContext, other);
  };

  // Reset
  const handleReset = () => {
    setStep("input");
    setAnalysis(null);
    setVersions({});
    setActiveVersion("enhanced");
    setLastContext(null);
    setError("");
  };

  if (step === "input") {
    return (
      <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <div className="pt-6 pb-2 text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-ink-900 text-balance sm:text-4xl">
              把课文变成一堂好课
            </h1>
            <p className="mt-4 text-sm leading-7 text-ink-500 text-pretty sm:text-base">
              粘贴或上传英文课文，自动完成词汇、文化与教学分析。
              <br className="hidden sm:block" />
              确认教案后，一键生成 PPT、Word 和网页课件。
            </p>
          </div>

          <InputStep
            title={title}
            setTitle={setTitle}
            text={text}
            setText={setText}
            wordCount={wordCount}
            loading={loading}
            onAnalyze={handleAnalyze}
          />

          {error && (
            <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="brand-surface px-6 py-6 sm:px-8 mb-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="min-w-0">
              <h1 className="truncate text-2xl font-semibold tracking-tight text-ink-900 sm:text-3xl">
                {title || "课文分析"}
              </h1>
              <p className="mt-2 text-sm text-ink-500">
                {step === "analysis" ? "查看分析结果，确认后生成教案。" : "审阅教案，确认后可生成课件。"}
              </p>
            </div>
            <button
              onClick={handleReset}
              className="btn-secondary self-start sm:self-auto"
            >
              换一篇课文
            </button>
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
          {step === "analysis" && analysis && (
            <AnalysisStep
              analysis={analysis}
              loading={loading}
              cultureStatus={cultureStatus}
              settings={{
                studentLevel,
                onStudentLevelChange: handleStudentLevelChange,
                recomputing,
                courseType,
                setCourseType,
                classSize,
                setClassSize,
                durationInput,
                setDurationInput,
                nativeLanguage,
                setNativeLanguage,
                planMode,
                setPlanMode,
              }}
              onNext={handleGenerateFromSettings}
              onBack={() => setStep("input")}
            />
          )}

          {step === "plan" && versions[activeVersion] && (
            <PlanStep
              result={versions[activeVersion]!}
              versions={versions}
              activeVersion={activeVersion}
              onSwitchVersion={setActiveVersion}
              onGenerateOther={handleGenerateOther}
              generatingOther={loading}
              onReset={handleReset}
              onUpdate={(mode, r) => setVersions((prev) => ({ ...prev, [mode]: r }))}
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
  const steps: { key: Step; label: string; icon: string; hint: string }[] = [
    { key: "input", label: "输入课文", icon: "📝", hint: "准备文本" },
    { key: "analysis", label: "课文分析", icon: "📊", hint: "形成判断" },
    { key: "plan", label: "教案", icon: "📋", hint: "进入课件" },
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
  wordCount,
  loading,
  onAnalyze,
}: {
  title: string;
  setTitle: (v: string) => void;
  text: string;
  setText: (v: string) => void;
  wordCount: number;
  loading: boolean;
  onAnalyze: () => void;
}) {
  return (
    <div>
      {/* 聚焦式输入区：标题内嵌顶端，正文占视口 60%（min 420px）自增高 */}
      <div className="workbench-panel mt-6 p-3 sm:p-4">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="课文标题（可选，上传文件时自动填入）"
          className="w-full border-b border-black/5 bg-transparent px-3 py-2.5 text-base font-medium text-ink-900 placeholder:font-normal placeholder:text-ink-400 outline-none"
        />
        <div className="relative">
          <div className="min-h-[max(420px,60vh)] pt-2">
            <TiptapEditor
              content={text}
              onChange={setText}
              frameless
              placeholder="把课文粘贴到这里，或点左下角上传文件..."
            />
          </div>
          <div className="absolute bottom-1.5 left-1 z-10">
            <FileUploadZone
              compact
              onTextExtracted={(extractedText) => setText(extractedText)}
              onFilename={(filename) => {
                if (!title) setTitle(filename.replace(/\.[^.]+$/, ""));
              }}
            />
          </div>
          <div className="pointer-events-none absolute bottom-2 right-2 text-xs text-ink-400">
            {wordCount > 0 && wordCount < 20
              ? `${wordCount} 词（至少 20 词才能分析）`
              : `${wordCount} 词`}
          </div>
        </div>
      </div>

      <div className="mt-5 flex justify-center">
        <button
          onClick={onAnalyze}
          disabled={loading || wordCount < 20}
          className="btn-primary px-10 py-3.5 text-base disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "分析中..." : "开始分析"}
        </button>
      </div>
    </div>
  );
}

// ============ 生成教案前确认（教学设置） ============

interface SettingsProps {
  studentLevel: string;
  onStudentLevelChange: (v: string) => void;
  recomputing: boolean;
  courseType: string;
  setCourseType: (v: string) => void;
  classSize: string;
  setClassSize: (v: string) => void;
  durationInput: string;
  setDurationInput: (v: string) => void;
  nativeLanguage: string;
  setNativeLanguage: (v: string) => void;
  planMode: "basic" | "enhanced";
  setPlanMode: (v: "basic" | "enhanced") => void;
}

function SettingsStrip(props: SettingsProps) {
  const {
    studentLevel,
    onStudentLevelChange,
    recomputing,
    courseType,
    setCourseType,
    classSize,
    setClassSize,
    durationInput,
    setDurationInput,
    nativeLanguage,
    setNativeLanguage,
    planMode,
    setPlanMode,
  } = props;

  const adjustDuration = (delta: number) => {
    const n = parseInt(durationInput, 10);
    const base = Number.isNaN(n) ? 90 : n;
    setDurationInput(String(Math.min(180, Math.max(5, base + delta))));
  };
  const durationNum = parseInt(durationInput, 10);
  const durationInvalid =
    durationInput !== "" && (!Number.isNaN(durationNum) && (durationNum < 5 || durationNum > 180));

  return (
    <div className="page-surface-strong px-5 py-5 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h3 className="text-sm font-semibold text-ink-800">生成教案前 · 确认教学设置</h3>
        {recomputing && (
          <span className="text-xs text-ink-400">正在按新水平重算难度差距…</span>
        )}
      </div>

      <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
        {/* 学生水平 */}
        <div className="sm:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-ink-700">学生水平</label>
          <div className="flex flex-wrap gap-2">
            {CEFR_LEVELS.map((level) => (
              <button
                key={level}
                onClick={() => onStudentLevelChange(level)}
                className={`rounded-xl border px-3.5 py-2 text-sm transition-colors ${
                  studentLevel === level
                    ? "border-primary-600 bg-primary-600 text-white"
                    : "border-black/10 bg-white text-ink-600 hover:border-primary-400"
                }`}
              >
                {cefrLabel(level)}
              </button>
            ))}
          </div>
        </div>

        {/* 课时长度 */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-700">课时长度（分钟）</label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => adjustDuration(-5)}
              className="btn-secondary h-9 w-9 !p-0 text-base"
              aria-label="减少 5 分钟"
            >
              −
            </button>
            <input
              type="text"
              inputMode="numeric"
              value={durationInput}
              onChange={(e) => setDurationInput(e.target.value.replace(/[^0-9]/g, ""))}
              onBlur={() => {
                const n = parseInt(durationInput, 10);
                if (durationInput === "" || Number.isNaN(n)) {
                  setDurationInput("90");
                } else {
                  setDurationInput(String(Math.min(180, Math.max(5, n))));
                }
              }}
              className="morandi-input w-24 text-center"
            />
            <button
              type="button"
              onClick={() => adjustDuration(5)}
              className="btn-secondary h-9 w-9 !p-0 text-base"
              aria-label="增加 5 分钟"
            >
              +
            </button>
            <span className="text-xs text-ink-400">5–180 分钟</span>
          </div>
          {durationInvalid && (
            <p className="mt-1.5 text-xs text-red-600">请输入 5 到 180 之间的数字</p>
          )}
        </div>

        {/* 课型 */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-700">课型</label>
          <select
            value={courseType}
            onChange={(e) => setCourseType(e.target.value)}
            className="morandi-input"
          >
            <option value="">未指定</option>
            {COURSE_TYPES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* 班级人数 */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-700">班级人数</label>
          <input
            type="number"
            value={classSize}
            onChange={(e) => setClassSize(e.target.value)}
            placeholder="例：30"
            min={1}
            max={200}
            className="morandi-input"
          />
        </div>

        {/* 学生母语 */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-700">学生母语</label>
          <select
            value={nativeLanguage}
            onChange={(e) => setNativeLanguage(e.target.value)}
            className="morandi-input"
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

        {/* 生成模式 */}
        <div className="sm:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-ink-700">生成模式</label>
          <div className="grid max-w-md grid-cols-2 gap-2">
            <button
              onClick={() => setPlanMode("basic")}
              className={`rounded-xl border p-3 text-left transition-colors ${
                planMode === "basic"
                  ? "border-primary-600 bg-primary-50"
                  : "border-black/10 bg-white hover:border-primary-300"
              }`}
            >
              <div className="text-sm font-medium text-ink-900">基础模式</div>
              <div className="mt-0.5 text-xs text-ink-500">快速生成基础教案</div>
            </button>
            <button
              onClick={() => setPlanMode("enhanced")}
              className={`rounded-xl border p-3 text-left transition-colors ${
                planMode === "enhanced"
                  ? "border-primary-600 bg-primary-50"
                  : "border-black/10 bg-white hover:border-primary-300"
              }`}
            >
              <div className="text-sm font-medium text-ink-900">增强模式</div>
              <div className="mt-0.5 text-xs text-ink-500">含依据引用与更细的教学设计</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ Step 2: Analysis ============

function AnalysisStep({
  analysis,
  loading,
  cultureStatus,
  settings,
  onNext,
  onBack,
}: {
  analysis: WhiteboxAnalysis;
  loading: boolean;
  cultureStatus: "idle" | "loading" | "enriched" | "fallback";
  settings: SettingsProps;
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="space-y-6">
      <SettingsStrip {...settings} />

      <div className="workbench-panel space-y-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="section-title mb-2">Step 2</div>
            <h2 className="text-2xl font-semibold text-ink-900">课文分析结果</h2>
          </div>
          <div className="rounded-full bg-canvas-200 px-4 py-2 text-xs font-medium text-ink-600 shadow-soft">
            耗时 {analysis.analysis_duration}s
          </div>
        </div>
        <WhiteboxResults data={analysis} cultureStatus={cultureStatus} />
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
          {loading ? "生成中..." : "生成教案"}
        </button>
      </div>
    </div>
  );
}

// ============ Step 3: Plan ============

function PlanStep({
  result,
  versions,
  activeVersion,
  onSwitchVersion,
  onGenerateOther,
  generatingOther,
  onReset,
  onUpdate,
  text,
  title,
  studentLevel,
  language,
}: {
  result: GeneratePlanResult;
  versions: { basic?: GeneratePlanResult; enhanced?: GeneratePlanResult };
  activeVersion: "basic" | "enhanced";
  onSwitchVersion: (v: "basic" | "enhanced") => void;
  onGenerateOther: () => void;
  generatingOther: boolean;
  onReset: () => void;
  onUpdate?: (mode: "basic" | "enhanced", r: GeneratePlanResult) => void;
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
  const [coursewareProgress, setCoursewareProgress] = useState("");
  const [blueprintConfirmed, setBlueprintConfirmed] = useState(false);
  const [planConfirmed, setPlanConfirmed] = useState(false);

  const availableVersions = (["basic", "enhanced"] as const).filter(
    (v) => versions[v]
  );

  // 切换版本时重置确认状态：新版本需要重新审阅
  const handleSwitchVersion = (v: "basic" | "enhanced") => {
    onSwitchVersion(v);
    setPlanConfirmed(false);
  };

  const handleCreateCourseware = async (format: "html" | "ppt" | "word") => {
    if (!text) {
      setRevisionError("课文内容缺失，无法生成课件，请重新分析");
      return;
    }
    setCreatingCourseware(true);
    setCoursewareProgress("正在启动 AI 生成…");
    try {
      const settings = result.generation_settings;
      const start = await apiPost<{ task_id: string }>("/courseware/generate", {
        format,
        title: result.text_title || "教学课件",
        plan: result.teaching_plan,
        analysis: {
          vocabulary: result.vocabulary,
          syntax: result.syntax,
          discourse: result.discourse,
        },
        text,
        language_name: result.language_name || "英语",
        text_level: result.text_level,
        student_level: result.student_level || studentLevel,
        duration_minutes: settings?.duration_minutes ?? 90,
        course_type: settings?.course_type,
        class_size: settings?.class_size,
        native_language: settings?.native_language,
        learner_gap: result.learner_gap,
        enhancement_tags: result.enhancement_tags,
      });
      // 轮询生成状态（上限 5 分钟）
      for (let i = 0; i < 100; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        const st = await apiGet<{
          status: string;
          progress?: string | null;
          project_id?: string;
          download_url?: string;
          fallback?: boolean;
          error?: string;
        }>(`/courseware/generate/${start.task_id}`);
        if (st.progress) setCoursewareProgress(st.progress);
        if (st.status === "done" && st.project_id) {
          if (format === "html") {
            if (st.fallback) {
              setCoursewareProgress("AI 完整生成暂不可用，已用简化版生成，即将进入编辑器…");
              await new Promise((r) => setTimeout(r, 1500));
            }
            router.push(`/courseware/${st.project_id}/edit`);
            return;
          }
          // PPT / Word：认证拉取产物并触发浏览器下载
          const ext = format === "ppt" ? "pptx" : "docx";
          const resp = await apiRequest("GET", st.download_url || "");
          if (!resp.ok) throw new Error("产物下载失败，请到课件列表重试");
          const blob = await resp.blob();
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = `${result.text_title || "教学课件"}.${ext}`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(a.href);
          setCoursewareProgress(
            st.fallback
              ? "AI 完整生成暂不可用，已下载简化版文档（可在历史记录中重新生成）"
              : "已生成并开始下载，可到「教学课件」查看项目"
          );
          await new Promise((r) => setTimeout(r, 4000));
          return;
        }
        if (st.status === "error") throw new Error(st.error || "课件生成失败，请重试");
      }
      throw new Error("生成超时（超过 5 分钟），请重试");
    } catch (e: unknown) {
      setRevisionError(e instanceof Error ? e.message : "课件生成失败，请重试");
    } finally {
      setCreatingCourseware(false);
      setCoursewareProgress("");
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
        onUpdate(activeVersion, {
          ...result,
          teaching_plan: resp.teaching_plan,
          generation_duration: resp.generation_duration,
          model: resp.model,
        });
      }
      // 教案内容已变化，需要重新确认
      setPlanConfirmed(false);
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
              difficult_words: result.vocabulary?.difficult_words || [],
              cultural_elements: result.cultural_elements || [],
              text_level: result.text_level,
              language_name: result.language_name,
            },
            format,
            title: result.text_title || "教学方案",
          }),
        }
      );

      if (!resp.ok) {
        const status = resp.status;
        const errData = await resp.json().catch(() => ({}));
        const detail = typeof errData.detail === "string" ? errData.detail : undefined;
        if (status === 401 || status === 403) throw new Error("登录已过期，请重新登录");
        if (status >= 500) throw new Error("服务暂时不可用，请稍后重试");
        throw new Error(detail || "导出失败，请稍后重试");
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
      setExportError(
        e instanceof TypeError
          ? "网络连接失败，请检查网络后重试"
          : e instanceof Error
            ? e.message
            : "导出失败"
      );
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

        {/* A/B 版本切换 */}
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {availableVersions.map((v) => (
            <button
              key={v}
              onClick={() => handleSwitchVersion(v)}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                activeVersion === v
                  ? "bg-primary-500 text-ink-900"
                  : "border border-black/10 bg-white text-ink-600 hover:bg-canvas-100"
              }`}
            >
              {v === "basic" ? "基础模式" : "增强模式"}
            </button>
          ))}
          {availableVersions.length < 2 && (
            <button
              onClick={onGenerateOther}
              disabled={generatingOther}
              className="rounded-xl border border-primary-300 bg-primary-50 px-4 py-2 text-sm font-medium text-primary-700 transition-colors hover:bg-primary-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {generatingOther
                ? "生成中..."
                : `生成${activeVersion === "basic" ? "增强" : "基础"}版本`}
            </button>
          )}
        </div>

        <div className="archive-surface p-4 mb-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="section-title mb-2">{planConfirmed ? "课件就绪" : "教案审阅"}</div>
              <p className="text-sm text-ink-600 leading-6">
                {planConfirmed
                  ? "教案已确认，可生成课件或进入 HTML 编辑器。"
                  : "审阅教案，必要时修订，确认后进入课件生成。"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-ink-500">
              {planConfirmed ? (
                <>
                  <span className="drawer-handle bg-white border border-black/5 text-ink-500">PPT / Word / HTML</span>
                  <span className="drawer-handle bg-sage-100 border border-sage-200 text-ink-600">HTML 可继续精修</span>
                </>
              ) : (
                <>
                  <span className="drawer-handle bg-white border border-black/5 text-ink-500">可修订教案</span>
                  <span className="drawer-handle bg-canvas-200 border border-black/5 text-ink-500">确认后生成课件</span>
                </>
              )}
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
            onExport={planConfirmed ? handleExport : undefined}
            exporting={exporting}
            onRevise={handleRevise}
            revising={revising}
            text={text}
            title={title}
            studentLevel={studentLevel}
            language={language}
            planConfirmed={planConfirmed}
            onConfirmPlan={() => setPlanConfirmed(true)}
            onUnconfirmPlan={() => setPlanConfirmed(false)}
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

      {/* Courseware entry — 仅在教案确认后显示 */}
      {planConfirmed && (
      <div className="archive-surface p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="w-11 h-11 rounded-2xl bg-canvas-300 flex items-center justify-center text-ink-700 shadow-soft">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <div className="flex-1 max-w-2xl">
              <div className="section-title mb-2">Courseware Generation</div>
              <h3 className="text-lg font-semibold text-ink-900">AI 三链路课件生成</h3>
              <p className="text-sm text-ink-500 mt-1 leading-6">
                同一确认教案，三种独立产物：HTML 交互课件（进编辑器精修）、PPT 课堂放映（含讲者备注）、Word 课堂执行文档（步骤表/板书/作业）。各自独立 LLM 按媒介最优化生成。
              </p>
            </div>
          </div>
          <div className="grid gap-2 lg:w-[360px]">
            <button
              onClick={() => handleCreateCourseware("html")}
              disabled={creatingCourseware}
              className="btn-primary w-full rounded-xl py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creatingCourseware ? "AI 生成中…" : "生成 HTML 课件（约 1-2 分钟）"}
            </button>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleCreateCourseware("ppt")}
                disabled={creatingCourseware}
                className="btn-secondary w-full rounded-xl py-3 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                生成 PPT
              </button>
              <button
                onClick={() => handleCreateCourseware("word")}
                disabled={creatingCourseware}
                className="btn-secondary w-full rounded-xl py-3 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                生成 Word 讲义
              </button>
            </div>
          </div>
        </div>
        {creatingCourseware && coursewareProgress && (
          <div className="mt-4 flex items-center gap-3 rounded-xl bg-canvas-200/60 px-4 py-3 text-sm text-ink-600">
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-ink-300 border-t-primary-600" />
            {coursewareProgress}
          </div>
        )}
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="data-card p-4 bg-white/90">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Create</div>
            <div className="mt-2 text-sm font-semibold text-ink-900">创建课件项目</div>
            <p className="mt-1 text-xs text-ink-500 leading-5">AI 按教案逐环节生成可交互课件，无需手动拼装。</p>
          </div>
          <div className="data-card p-4 bg-white/90">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Edit</div>
            <div className="mt-2 text-sm font-semibold text-ink-900">进入编辑器</div>
            <p className="mt-1 text-xs text-ink-500 leading-5">生成后自动跳转到编辑器，继续做页面与组件调整。</p>
          </div>
          <div className="data-card p-4 bg-white/90">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Present</div>
            <div className="mt-2 text-sm font-semibold text-ink-900">进入课堂展示</div>
            <p className="mt-1 text-xs text-ink-500 leading-5">在课件项目内进入课堂展示模式。</p>
          </div>
        </div>
      </div>
      )}

      <PlanEvaluationForm chosenVersion={activeVersion} />

      <button
        onClick={onReset}
        className="btn-secondary w-full rounded-xl py-3"
      >
        分析新课文
      </button>
    </div>
  );
}
