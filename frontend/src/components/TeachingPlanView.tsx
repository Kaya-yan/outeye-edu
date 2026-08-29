"use client";

import { useState } from "react";
import { Evidence } from "@/lib/analysis";
import EvidenceDrawer from "./EvidenceDrawer";

interface Activity {
  name?: string;
  objective?: string;
  steps?: string;
  duration?: string;
  assessment?: string;
  evidence?: Evidence[];
  degraded?: boolean;
}

interface Objective {
  text: string;
  bloom?: string;
  assessment?: string;
}

interface TeachingPlanData {
  framework?: string;
  objectives?: Objective[];
  difficulty_overview: string;
  teaching_suggestions: string[];
  activity_designs: Activity[];
  assessment?: { formative?: string[]; summative?: string[] };
  differentiation: string;
  theoretical_basis: string;
  self_check?: Record<string, unknown>;
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
  planConfirmed,
  onConfirmPlan,
  onUnconfirmPlan,
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
  planConfirmed?: boolean;
  onConfirmPlan?: () => void;
  onUnconfirmPlan?: () => void;
}) {
  const [revisionTarget, setRevisionTarget] = useState<SectionKey | null>(null);
  const [revisionText, setRevisionText] = useState("");
  const [evidenceIndex, setEvidenceIndex] = useState<number | null>(null);

  const handleRevise = async () => {
    if (!onRevise || !revisionText.trim()) return;
    await onRevise(revisionText.trim(), revisionTarget || undefined);
    setRevisionText("");
    setRevisionTarget(null);
  };

  // 自检结果：未过项黄条提示；降级生成灰条明示
  const sc = plan.self_check as Record<string, unknown> | undefined;
  const scFailed: string[] = [];
  if (sc) {
    if (!sc.objectives_count) scFailed.push("缺少教学目标");
    if (sc.objectives_measurable === false) scFailed.push("目标可测量性未通过");
    if (!sc.stage_count) scFailed.push("缺少课堂环节");
    if (sc.time_matches_duration === false)
      scFailed.push(`环节时间总和 ${String(sc.time_sum_minutes ?? "?")} 分钟与课时不符`);
    if (Number(sc.formative_checks ?? 9) < 2) scFailed.push("形成性评估点不足 2 个");
    if (Number(sc.summative_checks ?? 9) < 2) scFailed.push("终结性评估点不足 2 个");
    if (sc.no_copy_paste === false) scFailed.push("疑似照抄课文");
  }
  const isFallback =
    model === "template-fallback" || sc?.prompt_version === "fallback";

  return (
    <div className="space-y-6">
      {isFallback && (
        <div className="flex items-start gap-2 rounded-xl border border-gray-200 bg-gray-50 p-3">
          <span className="text-sm">⚠️</span>
          <p className="text-xs leading-5 text-gray-600">
            简化版生成：AI 服务暂不可用，本教案由模板生成，教学目标与时间分配为默认值，请人工核对后再使用。
          </p>
        </div>
      )}
      {sc && scFailed.length > 0 && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3">
          <span className="text-sm">📋</span>
          <div className="text-xs leading-5 text-amber-800">
            <span className="font-semibold">教案自检提示：</span>
            {scFailed.join("；")}。
            {typeof sc.notes === "string" && sc.notes && `（${sc.notes}）`}
          </div>
        </div>
      )}

      {/* Framework */}
      {plan.framework && (
        <Section title="教学设计框架" icon="🧭">
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
            {plan.framework}
          </p>
        </Section>
      )}

      {/* Objectives */}
      {plan.objectives && plan.objectives.length > 0 && (
        <Section title="教学目标" icon="🎯">
          <div className="space-y-3">
            {plan.objectives.map((obj, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className="flex-shrink-0 px-2 py-0.5 text-xs font-medium rounded bg-primary-100 text-primary-700">
                  目标 {i + 1}
                </span>
                <div className="flex-1">
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {obj.text}
                    {obj.bloom && (
                      <span className="ml-2 inline-block px-1.5 py-0.5 text-[10px] font-medium rounded bg-green-50 text-green-700 border border-green-200">
                        Bloom·{obj.bloom}
                      </span>
                    )}
                  </p>
                  {obj.assessment && (
                    <p className="mt-1 text-xs text-gray-500">
                      <span className="font-medium">评估方式：</span>
                      {obj.assessment}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

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
                className="border border-gray-200 rounded-lg p-4 hover:border-primary-500/30 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2 py-0.5 text-xs font-medium rounded bg-primary-100 text-primary-700">
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
                {act.assessment && (
                  <div className="text-xs text-gray-500 mb-1">
                    <span className="font-medium">评估点：</span>{act.assessment}
                  </div>
                )}
                {act.duration && (
                  <div className="text-xs text-gray-500">
                    <span className="font-medium">时间：</span>{act.duration}
                  </div>
                )}
                {((act.evidence && act.evidence.length > 0) || act.degraded) && (
                  <div className="mt-2">
                    <button
                      onClick={() => setEvidenceIndex(evidenceIndex === i ? null : i)}
                      className={`text-xs flex items-center gap-1 ${
                        act.degraded
                          ? "text-ink-400 hover:text-ink-500"
                          : "text-primary-700 hover:text-primary-600"
                      }`}
                    >
                      <span className={`transition-transform ${evidenceIndex === i ? "rotate-90" : ""}`}>▶</span>
                      {evidenceIndex === i
                        ? "收起设计依据"
                        : act.degraded
                        ? "设计依据（已降级）"
                        : `设计依据 (${act.evidence!.length})`}
                    </button>
                    {evidenceIndex === i && (
                      <div className="mt-2">
                        <EvidenceDrawer evidence={act.evidence || []} degraded={act.degraded} />
                      </div>
                    )}
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

      {/* Assessment Design */}
      {plan.assessment &&
        ((plan.assessment.formative?.length ?? 0) > 0 ||
          (plan.assessment.summative?.length ?? 0) > 0) && (
          <Section title="评估设计" icon="✅">
            <div className="space-y-3">
              {(plan.assessment.formative?.length ?? 0) > 0 && (
                <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                  <div className="text-xs font-semibold text-blue-700 mb-1.5">形成性评估（课中）</div>
                  <ul className="space-y-1">
                    {plan.assessment.formative!.map((item, i) => (
                      <li key={i} className="text-xs text-gray-700 leading-relaxed flex gap-1.5">
                        <span className="text-blue-400">•</span>{item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(plan.assessment.summative?.length ?? 0) > 0 && (
                <div className="p-3 rounded-lg bg-green-50 border border-green-200">
                  <div className="text-xs font-semibold text-green-700 mb-1.5">终结性评估（课后）</div>
                  <ul className="space-y-1">
                    {plan.assessment.summative!.map((item, i) => (
                      <li key={i} className="text-xs text-gray-700 leading-relaxed flex gap-1.5">
                        <span className="text-green-400">•</span>{item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
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

      {/* 教案确认闸门：未确认时显示"确认教案" CTA；已确认时显示导出按钮 + 返回修订 */}
      {planConfirmed ? (
        <div className="pt-4 border-t border-gray-100 space-y-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1 rounded-full bg-sage-100 px-2.5 py-1 text-sage-700 border border-sage-200">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
              教案已确认
            </span>
            {onUnconfirmPlan && (
              <button
                onClick={onUnconfirmPlan}
                className="text-xs text-ink-500 hover:text-ink-700 underline-offset-2 hover:underline"
              >
                返回修订
              </button>
            )}
          </div>
          {onExport && (
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => onExport("docx")}
                disabled={exporting}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {exporting ? "导出中…" : "导出完整版 Word 教案"}
              </button>
            </div>
          )}
        </div>
      ) : (
        onConfirmPlan && (
          <div className="pt-4 border-t border-gray-100">
            <div className="rounded-xl bg-primary-50 border border-primary-200 p-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-primary-500 text-white flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-ink-900 mb-1">确认教案后进入课件生成</div>
                  <p className="text-xs text-ink-600 leading-5 mb-3">
                    教案确认后即可生成 PPT / Word / HTML 课件。如有需要修改的地方，请先用上方“修改”按钮调整。
                  </p>
                  <button
                    onClick={onConfirmPlan}
                    className="btn-primary rounded-full px-5 py-2 text-sm"
                  >
                    确认教案，进入课件生成
                  </button>
                </div>
              </div>
            </div>
          </div>
        )
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
            className="text-xs text-primary-700 hover:text-primary-600 border border-primary-200 rounded px-2 py-0.5 hover:bg-primary-50 transition-colors"
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
        placeholder="输入修改意见，如：活动时间太长、请换成小组活动、第2条建议不适合我的学生…"
        className="w-full text-sm border border-amber-300 rounded p-2 bg-white resize-none focus:outline-none focus:ring-1 focus:ring-primary-500"
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
          className="px-3 py-1 text-xs text-white bg-primary-600 rounded hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "修订中…" : "重新生成"}
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

  // 依据预览长度阈值：超过 200 字才折叠
  const PREVIEW_THRESHOLD = 200;

  const renderEvidenceBlock = (
    label: string,
    color: "blue" | "green",
    content: string
  ) => {
    const isLong = content.length > PREVIEW_THRESHOLD;
    const preview = isLong && !expanded ? content.slice(0, PREVIEW_THRESHOLD) + "…" : content;
    return (
      <div className={`p-2 rounded border ${
        color === "blue" ? "bg-blue-50 border-blue-200" : "bg-green-50 border-green-200"
      }`}>
        <div className={`text-[10px] font-semibold mb-1 ${color === "blue" ? "text-blue-600" : "text-green-600"}`}>
          {label}
        </div>
        <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap">{preview}</p>
        {isLong && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-1 text-[11px] text-primary-700 hover:text-primary-600 link-underline"
          >
            {expanded ? "收起" : "展开全部"}
          </button>
        )}
      </div>
    );
  };

  return (
    <li className="flex items-start gap-3">
      <span className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center text-xs font-bold flex-shrink-0">
        {index + 1}
      </span>
      <div className="flex-1">
        <p className="text-sm text-gray-700 leading-relaxed">{mainText}</p>
        {hasChain && (
          <div className="mt-2 space-y-2">
            {dataMatch && renderEvidenceBlock("数据依据", "blue", dataMatch[1].trim())}
            {theoryMatch && renderEvidenceBlock("理论依据", "green", theoryMatch[1].trim())}
          </div>
        )}
      </div>
    </li>
  );
}
