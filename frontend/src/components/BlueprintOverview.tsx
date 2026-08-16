"use client";

import { Blueprint } from "@/lib/analysis";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-black/5 bg-canvas-50 p-4">
      <div className="mb-2 text-sm font-semibold text-ink-900">{title}</div>
      {children}
    </div>
  );
}

export default function BlueprintOverview({
  blueprint,
  onConfirm,
}: {
  blueprint: Blueprint;
  onConfirm: () => void;
}) {
  return (
    <div className="archive-surface p-6 space-y-4">
      <div>
        <div className="section-title mb-1">Teaching Blueprint</div>
        <h2 className="text-xl font-semibold text-ink-900">教学设计总览</h2>
        <p className="mt-1 text-sm text-ink-500">
          确认教学蓝图后，展开完整教案。
        </p>
      </div>

      <Section title="教学目标">
        {blueprint.objectives.length > 0 ? (
          <ul className="space-y-1.5">
            {blueprint.objectives.map((o, i) => (
              <li key={i} className="text-sm text-ink-600">
                <span className="mr-1 text-primary-700">▪</span>
                {o.objective}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-ink-400">暂无明确目标</p>
        )}
      </Section>

      <Section title="阶段安排">
        {blueprint.stages.length > 0 ? (
          <ul className="space-y-1.5">
            {blueprint.stages.map((s, i) => (
              <li key={i} className="text-sm text-ink-600">
                <span className="mr-1.5 rounded bg-primary-100 px-1.5 py-0.5 text-xs font-medium text-ink-800">
                  {s.stage}
                </span>
                {s.activities.join("、")}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-ink-400">暂无活动</p>
        )}
      </Section>

      <Section title="时间预算">
        <p className="text-sm text-ink-600">
          总时长 <span className="font-semibold text-ink-900">{blueprint.time_budget.total_minutes}</span> 分钟
          {blueprint.time_budget.activities.length > 0 && (
            <span className="ml-1 text-xs text-ink-400">
              （{blueprint.time_budget.activities.map((a) => `${a.name} ${a.minutes}min`).join(" · ")}）
            </span>
          )}
        </p>
      </Section>

      <Section title="评价点">
        {blueprint.evaluation_points.length > 0 ? (
          <ul className="space-y-1.5">
            {blueprint.evaluation_points.map((p, i) => (
              <li key={i} className="text-sm text-ink-600">
                <span className="mr-1 text-sage-600">▪</span>
                {p}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-ink-400">暂无评价点</p>
        )}
      </Section>

      <Section title="关键证据类型">
        <p className="text-sm text-ink-600">
          理论依据 <span className="font-semibold text-ink-900">{blueprint.evidence_types.theory}</span> 条 · 教学资源{" "}
          <span className="font-semibold text-ink-900">{blueprint.evidence_types.resource}</span> 条
        </p>
      </Section>

      <button onClick={onConfirm} className="btn-primary w-full rounded-xl py-3">
        确认，查看完整教案
      </button>
    </div>
  );
}
