"use client";

import { useState } from "react";

interface Activity {
  name?: string;
  objective?: string;
  steps?: string;
  duration?: string;
}

interface TeachingPlanData {
  difficulty_overview: string;
  teaching_suggestions: string[];
  activity_designs: Activity[];
  differentiation: string;
  theoretical_basis: string;
}

interface Source {
  type: string;
  title?: string;
  score?: number;
}

type SectionKey = "difficulty_overview" | "suggestions" | "activities" | "differentiation" | "theory";

const SECTION_MAP: Record<SectionKey, string> = {
  difficulty_overview: "difficulty_overview",
  suggestions: "suggestions",
  activities: "activities",
  differentiation: "differentiation",
  theory: "theory",
};

export default function TeachingPlanView({
  plan,
  sources,
  model,
  duration,
  onExport,
  exporting,
  onRevise,
  revising,
  text,
  title,
  studentLevel,
  language,
}: {
  plan: TeachingPlanData;
  sources: Source[];
  model: string;
  duration: number;
  onExport?: (format: "pptx" | "docx" | "html") => void;
  exporting?: boolean;
  onRevise?: (instruction: string, section?: string) => Promise<void>;
  revising?: boolean;
  text?: string;
  title?: string;
  studentLevel?: string;
  language?: string;
}) {
  const [revisionTarget, setRevisionTarget] = useState<SectionKey | null>(null);
  const [revisionText, setRevisionText] = useState("");

  const handleRevise = async () => {
    if (!onRevise || !revisionText.trim()) return;
    await onRevise(revisionText.trim(), revisionTarget || undefined);
    setRevisionText("");
    setRevisionTarget(null);
  };

  return (
    <div className="space-y-6">
      {/* Difficulty Overview */}
      <Section
        title="课文难度概述"
        icon="📊"
        sectionKey="difficulty_overview"
        revisionTarget={revisionTarget}
        onStartRevise={setRevisionTarget}
        hasRevise={!!onRevise}
      >
        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
          {plan.difficulty_overview}
        </p>
        {revisionTarget === "difficulty_overview" && (
          <RevisionInput
            value={revisionText}
            onChange={setRevisionText}
            onSubmit={handleRevise}
            onCancel={() => { setRevisionTarget(null); setRevisionText(""); }}
            loading={revising}
          />
        )}
      </Section>

      {/* Teaching Suggestions */}
      <Section
        title="教学建议"
        icon="💡"
        sectionKey="suggestions"
        revisionTarget={revisionTarget}
        onStartRevise={setRevisionTarget}
        hasRevise={!!onRevise}
      >
        <ol className="space-y-3">
          {plan.teaching_suggestions.map((s, i) => (
            <SuggestionItem key={i} index={i} text={s} />
          ))}
        </ol>
        {revisionTarget === "suggestions" && (
          <RevisionInput
            value={revisionText}
            onChange={setRevisionText}
            onSubmit={handleRevise}
            onCancel={() => { setRevisionTarget(null); setRevisionText(""); }}
            loading={revising}
          />
        )}
      </Section>

      {/* Activity Designs */}
      {plan.activity_designs.length > 0 && (
        <Section
          title="课堂活动设计"
          icon="🎯"
          sectionKey="activities"
          revisionTarget={revisionTarget}
          onStartRevise={setRevisionTarget}
          hasRevise={!!onRevise}
        >
          <div className="space-y-4">
            {plan.activity_designs.map((act, i) => (
              <div
                key={i}
                className="border border-gray-200 rounded-lg p-4 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2 py-0.5 text-xs font-medium rounded bg-primary/10 text-primary">
                    活动 {i + 1}
                  </span>
                  {act.name && (
                    <span className="text-sm font-semibold text-gray-800">{act.name}</span>
                  )}
                </div>
                {act.objective && (
                  <div className="text-xs text-gray-500 mb-1">
                    <span className="font-medium">目标：</span>{act.objective}
                  </div>
                )}
                {act.steps && (
                  <div className="text-xs text-gray-500 mb-1">
                    <span className="font-medium">步骤：</span>{act.steps}
                  </div>
                )}
                {act.duration && (
                  <div className="text-xs text-gray-500">
                    <span className="font-medium">时间：</span>{act.duration}
                  </div>
                )}
              </div>
            ))}
          </div>
          {revisionTarget === "activities" && (
            <RevisionInput
              value={revisionText}
              onChange={setRevisionText}
              onSubmit={handleRevise}
              onCancel={() => { setRevisionTarget(null); setRevisionText(""); }}
              loading={revising}
            />
          )}
        </Section>
      )}

      {/* Differentiation */}
      {plan.differentiation && (
        <Section
          title="差异化教学策略"
          icon="🎯"
          sectionKey="differentiation"
          revisionTarget={revisionTarget}
          onStartRevise={setRevisionTarget}
          hasRevise={!!onRevise}
        >
          <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
            {plan.differentiation.split('\n').map((line, i) => {
              const trimmed = line.trim();
              if (trimmed.startsWith('- **基础层**') || trimmed.startsWith('**基础层**')) {
                return <div key={i} className="mb-2 p-2 bg-green-50 rounded border border-green-200"><span className="text-xs font-semibold text-green-700">基础层</span><p className="text-xs mt-1">{trimmed.replace(/^[-*]\s*\*?\*?基础层\*?\*?\s*[：:]?\s*/, '')}</p></div>;
              }
              if (trimmed.startsWith('- **进阶层**') || trimmed.startsWith('**进阶层**')) {
                return <div key={i} className="mb-2 p-2 bg-blue-50 rounded border border-blue-200"><span className="text-xs font-semibold text-blue-700">进阶层</span><p className="text-xs mt-1">{trimmed.replace(/^[-*]\s*\*?\*?进阶层\*?\*?\s*[：:]?\s*/, '')}</p></div>;
              }
              if (trimmed.startsWith('- **挑战层**') || trimmed.startsWith('**挑战层**')) {
                return <div key={i} className="mb-2 p-2 bg-orange-50 rounded border border-orange-200"><span className="text-xs font-semibold text-orange-700">挑战层</span><p className="text-xs mt-1">{trimmed.replace(/^[-*]\s*\*?\*?挑战层\*?\*?\s*[：:]?\s*/, '')}</p></div>;
              }
              return trimmed ? <p key={i}>{line}</p> : null;
            })}
          </div>
          {revisionTarget === "differentiation" && (
            <RevisionInput
              value={revisionText}
              onChange={setRevisionText}
              onSubmit={handleRevise}
              onCancel={() => { setRevisionTarget(null); setRevisionText(""); }}
              loading={revising}
            />
          )}
        </Section>
      )}

      {/* Theoretical Basis */}
      {plan.theoretical_basis && (
        <Section
          title="理论依据"
          icon="📚"
          sectionKey="theory"
          revisionTarget={revisionTarget}
          onStartRevise={setRevisionTarget}
          hasRevise={!!onRevise}
        >
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
            {plan.theoretical_basis}
          </p>
          {revisionTarget === "theory" && (
            <RevisionInput
              value={revisionText}
              onChange={setRevisionText}
              onSubmit={handleRevise}
              onCancel={() => { setRevisionTarget(null); setRevisionText(""); }}
              loading={revising}
            />
          )}
        </Section>
      )}

      {/* Sources */}
      {sources.length > 0 && (
        <Section title="参考来源" icon="🔗">
          <div className="flex flex-wrap gap-2">
            {sources.map((src, i) => (
              <span
                key={i}
                className={`px-2 py-1 text-xs rounded-full ${
                  src.type === "wiki"
                    ? "bg-blue-50 text-blue-700 border border-blue-200"
                    : "bg-green-50 text-green-700 border border-green-200"
                }`}
              >
                {src.type === "wiki" ? "📖 Wiki" : "📄 文档"}
                {src.title && `: ${src.title}`}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Export Buttons */}
      {onExport && (
        <div className="flex gap-3 pt-4 border-t border-gray-100">
          <button
            onClick={() => onExport("pptx")}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-orange-500 rounded-lg hover:bg-orange-600 disabled:opacity-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {exporting ? "导出中..." : "导出 PPT"}
          </button>
          <button
            onClick={() => onExport("docx")}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {exporting ? "导出中..." : "导出 Word"}
          </button>
          <button
            onClick={() => onExport("html")}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            {exporting ? "导出中..." : "导出 HTML"}
          </button>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center gap-4 text-xs text-gray-400 pt-2">
        <span>模型: {model}</span>
        <span>生成耗时: {duration}s</span>
      </div>
    </div>
  );
}

function Section({
  title,
  icon,
  sectionKey,
  revisionTarget,
  onStartRevise,
  hasRevise,
  children,
}: {
  title: string;
  icon: string;
  sectionKey?: SectionKey;
  revisionTarget?: SectionKey | null;
  onStartRevise?: (key: SectionKey) => void;
  hasRevise?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
          <span>{icon}</span>
          {title}
        </h3>
        {hasRevise && sectionKey && onStartRevise && revisionTarget !== sectionKey && (
          <button
            onClick={() => onStartRevise(sectionKey)}
            className="text-xs text-primary hover:text-primary/80 border border-primary/20 rounded px-2 py-0.5 hover:bg-primary/5 transition-colors"
          >
            修改
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

function RevisionInput({
  value,
  onChange,
  onSubmit,
  onCancel,
  loading,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  loading?: boolean;
}) {
  return (
    <div className="mt-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="输入修改意见，如：活动时间太长、请换成小组活动、第2条建议不适合我的学生..."
        className="w-full text-sm border border-amber-300 rounded p-2 bg-white resize-none focus:outline-none focus:ring-1 focus:ring-primary"
        rows={3}
      />
      <div className="flex gap-2 mt-2 justify-end">
        <button
          onClick={onCancel}
          className="px-3 py-1 text-xs text-gray-600 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
        >
          取消
        </button>
        <button
          onClick={onSubmit}
          disabled={!value.trim() || loading}
          className="px-3 py-1 text-xs text-white bg-primary rounded hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? "修订中..." : "重新生成"}
        </button>
      </div>
    </div>
  );
}

function SuggestionItem({ index, text }: { index: number; text: string }) {
  const [expanded, setExpanded] = useState(false);

  // 解析因果链结构：**建议N**：... **数据依据**：... **理论依据**：...
  const dataMatch = text.match(/[-*]\s*\*?\*?数据依据\*?\*?\s*[：:]\s*([\s\S]*?)(?=[-*]\s*\*?\*?理论依据|$)/);
  const theoryMatch = text.match(/[-*]\s*\*?\*?理论依据\*?\*?\s*[：:]\s*([\s\S]*?)$/);

  const hasChain = dataMatch || theoryMatch;

  // 提取建议正文（去掉数据依据和理论依据部分）
  let mainText = text;
  if (hasChain) {
    mainText = text.replace(/[-*]\s*\*?\*?(?:数据|理论)依据\*?\*?\s*[：:][\s\S]*/g, "").trim();
    // 清理 **建议N**：前缀
    mainText = mainText.replace(/^\*?\*?建议\d*\*?\*?\s*[：:]\s*/, "").trim();
  }

  return (
    <li className="flex items-start gap-3">
      <span className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center text-xs font-bold flex-shrink-0">
        {index + 1}
      </span>
      <div className="flex-1">
        <p className="text-sm text-gray-700 leading-relaxed">{mainText}</p>
        {hasChain && (
          <>
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-1 text-xs text-primary hover:text-primary/80 flex items-center gap-1"
            >
              <span className={`transition-transform ${expanded ? "rotate-90" : ""}`}>▶</span>
              {expanded ? "收起依据" : "查看依据"}
            </button>
            {expanded && (
              <div className="mt-2 space-y-2">
                {dataMatch && (
                  <div className="p-2 bg-blue-50 rounded border border-blue-200">
                    <div className="text-[10px] font-semibold text-blue-600 mb-1">数据依据</div>
                    <p className="text-xs text-gray-700">{dataMatch[1].trim()}</p>
                  </div>
                )}
                {theoryMatch && (
                  <div className="p-2 bg-green-50 rounded border border-green-200">
                    <div className="text-[10px] font-semibold text-green-600 mb-1">理论依据</div>
                    <p className="text-xs text-gray-700">{theoryMatch[1].trim()}</p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </li>
  );
}
