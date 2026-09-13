"use client";

import { Fragment, useRef, useState } from "react";

export interface BlueprintPage {
  kind: string;
  title: string;
  intent: string;
  para: number[] | null;
  chapter?: string | null;
}

export interface BlueprintMeta {
  source: string;
  note: string | null;
  n_paras: number;
  accent: string;
}

const KIND_LABELS: Record<string, string> = {
  cover: "封面节",
  agenda: "目标节",
  vocab: "词汇预教节",
  text_anatomy: "原文解剖节",
  lang_points: "语言点节",
  deep_reading: "精讲节",
  language_focus: "语言聚焦节",
  interaction: "互动检测节",
  summary: "总结节",
};

// 与后端 _CHAPTER_KIND_LABELS 保持一致：无显式章标签时按节型派生
const KIND_CHAPTER_LABELS: Record<string, string> = {
  cover: "导入",
  agenda: "导入",
  vocab: "词汇预教",
  text_anatomy: "课文精讲",
  lang_points: "课文精讲",
  deep_reading: "课文精讲",
  language_focus: "语法聚焦",
  interaction: "课堂活动",
  summary: "总结作业",
};

const ANATOMY_KINDS = new Set(["text_anatomy", "deep_reading"]);

const ADDABLE_KINDS = ["interaction", "language_focus", "vocab", "agenda"];
const MAX_CHAPTERS = 10;
const MAX_SECTIONS_PER_CHAPTER = 6;

function deriveChapters(pages: BlueprintPage[]) {
  const groups: { label: string; display: string; start: number; count: number }[] = [];
  pages.forEach((p, i) => {
    const label = (p.chapter || "").trim() || KIND_CHAPTER_LABELS[p.kind] || "内容";
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.count += 1;
    else groups.push({ label, display: label, start: i, count: 1 });
  });
  const counts: Record<string, number> = {};
  groups.forEach((g) => {
    counts[g.label] = (counts[g.label] || 0) + 1;
  });
  const seen: Record<string, number> = {};
  const cn = "一二三四五六七八九十";
  groups.forEach((g) => {
    if (counts[g.label] > 1) {
      seen[g.label] = (seen[g.label] || 0) + 1;
      const n = seen[g.label];
      g.display = n <= cn.length ? `${g.label}（${cn[n - 1]}）` : `${g.label}（${n}）`;
    }
  });
  return groups;
}

export default function PageBlueprintEditor({
  pages,
  meta,
  edits,
  busy,
  onPagesChange,
  onEdit,
  onConfirm,
  onReplan,
}: {
  pages: BlueprintPage[];
  meta: BlueprintMeta | null;
  edits: number;
  busy: boolean;
  onPagesChange: (next: BlueprintPage[]) => void;
  onEdit: () => void;
  onConfirm: () => void;
  onReplan: () => void;
}) {
  const [addKind, setAddKind] = useState(ADDABLE_KINDS[0]);
  const dragIndex = useRef<number | null>(null);
  const focusValue = useRef("");

  const chapters = deriveChapters(pages);
  const chapterAt = new Map<number, { no: number; display: string; count: number }>();
  chapters.forEach((g, gi) => chapterAt.set(g.start, { no: gi + 1, display: g.display, count: g.count }));
  const overChapterCap = chapters.length > MAX_CHAPTERS || chapters.some((g) => g.count > MAX_SECTIONS_PER_CHAPTER);

  const covered = new Set<number>();
  // 只有解剖类节型承担段落覆盖；语言点节与解剖节同锚，重复计数会掩盖漏段
  pages.forEach((p) => {
    if (ANATOMY_KINDS.has(p.kind)) (p.para || []).forEach((n) => covered.add(n));
  });
  const missingParas =
    meta && meta.n_paras > 0
      ? Array.from({ length: meta.n_paras }, (_, i) => i + 1).filter((n) => !covered.has(n))
      : [];

  const mutate = (next: BlueprintPage[]) => {
    onPagesChange(next);
    onEdit();
  };

  const updateField = (i: number, field: "title" | "intent", value: string) => {
    const next = [...pages];
    next[i] = { ...next[i], [field]: value };
    onPagesChange(next);
  };

  const commitEdit = (value: string) => {
    if (value !== focusValue.current) onEdit();
  };

  const deletePage = (i: number) => {
    mutate(pages.filter((_, idx) => idx !== i));
  };

  const addPage = () => {
    const page: BlueprintPage = { kind: addKind, title: KIND_LABELS[addKind] || addKind, intent: "", para: null, chapter: null };
    const next = [...pages];
    const at = next.length > 0 && next[next.length - 1].kind === "summary" ? next.length - 1 : next.length;
    next.splice(at, 0, page);
    mutate(next);
  };

  const reorder = (from: number, to: number) => {
    if (from === to) return;
    const next = [...pages];
    const [moved] = next.splice(from, 1);
    let at = Math.max(0, Math.min(to, next.length));
    // 封面固定首节、总结固定末节：非封面/总结节不允许落在首尾之外
    if (moved.kind !== "cover" && next.length > 0 && next[0].kind === "cover") at = Math.max(1, at);
    if (moved.kind !== "summary" && next.length > 0 && next[next.length - 1].kind === "summary")
      at = Math.min(at, next.length - 1);
    next.splice(at, 0, moved);
    mutate(next);
  };

  return (
    <div className="archive-surface mt-4 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <div className="section-title mb-1">Chapter Blueprint</div>
          <h3 className="text-lg font-semibold text-ink-900">
            课件章节蓝图（{chapters.length} 章 · {pages.length} 节）
          </h3>
          <p className="mt-1 text-sm leading-6 text-ink-500">
            确认后 AI 按此蓝图逐节生成。可编辑每节标题与教学意图、拖动调整顺序、删除或新增节；封面与总结节固定首尾。
            章按连续同环节自动归并，拖动跨环节会改变章归属。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {edits > 0 && (
            <span className="rounded-full bg-canvas-200 px-2.5 py-1 text-xs text-ink-600">已编辑 {edits} 处</span>
          )}
          <button
            onClick={onReplan}
            disabled={busy}
            className="btn-secondary rounded-xl px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            重新规划
          </button>
          <button
            onClick={onConfirm}
            disabled={busy || pages.length === 0}
            className="btn-primary rounded-xl px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy ? "生成中…" : "确认并生成 HTML 课件"}
          </button>
        </div>
      </div>

      {meta?.source === "fallback" && (
        <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs leading-5 text-amber-800">
          AI 规划未通过校验，已用模板规划兜底{meta.note ? `（${meta.note}）` : ""}。可直接编辑后确认，或点击「重新规划」再试。
        </p>
      )}
      {missingParas.length > 0 && (
        <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs leading-5 text-amber-800">
          第 {missingParas.join("、")} 段未被原文解剖节覆盖：确认生成时将自动改用内部规划补齐，建议为这些段落保留或补回解剖节。
        </p>
      )}
      {overChapterCap && (
        <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs leading-5 text-amber-800">
          当前结构超出章节上限（章 ≤{MAX_CHAPTERS}、每章 ≤{MAX_SECTIONS_PER_CHAPTER} 节）：确认生成时将自动拆分或合并章节，锚定课文的节不会丢失。
        </p>
      )}

      <div className="mt-4 space-y-2">
        {pages.map((p, i) => {
          const locked = p.kind === "cover" || p.kind === "summary";
          const draggable = !busy && !locked;
          const ch = chapterAt.get(i);
          return (
            <Fragment key={i}>
              {ch && (
                <div className="flex items-center gap-2 pt-2 first:pt-0">
                  <span className="text-xs font-semibold tracking-wide text-primary-700">
                    第 {ch.no} 章 · {ch.display}
                  </span>
                  <span className="text-[11px] text-ink-400">{ch.count} 节</span>
                  <div className="h-px flex-1 bg-black/10" />
                </div>
              )}
              <div
                draggable={draggable}
                onDragStart={() => {
                  dragIndex.current = i;
                }}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => {
                  if (dragIndex.current !== null) {
                    reorder(dragIndex.current, i);
                    dragIndex.current = null;
                  }
                }}
                className={`flex items-start gap-2.5 rounded-xl border border-black/10 bg-white p-2.5 ${
                  draggable ? "cursor-grab active:cursor-grabbing" : ""
                }`}
              >
                <span className="mt-1 select-none text-sm text-ink-300" title={locked ? "封面/总结节固定首尾" : "拖动调整顺序"}>
                  ⋮⋮
                </span>
                <span className="mt-0.5 w-6 shrink-0 text-center text-xs font-semibold text-ink-400">{i + 1}</span>
                <span className="mt-0.5 w-[92px] shrink-0 rounded-lg bg-primary-100 px-2 py-1 text-center text-xs font-medium text-primary-800">
                  {KIND_LABELS[p.kind] || p.kind}
                </span>
                <div className="grid flex-1 gap-1.5">
                  <input
                    value={p.title}
                    disabled={busy}
                    placeholder="节标题"
                    onFocus={() => {
                      focusValue.current = p.title;
                    }}
                    onBlur={() => commitEdit(p.title)}
                    onChange={(e) => updateField(i, "title", e.target.value)}
                    className="w-full rounded-lg border border-black/10 px-2.5 py-1.5 text-sm text-ink-900 focus:border-primary-300 focus:outline-none disabled:bg-canvas-50"
                  />
                  <input
                    value={p.intent}
                    disabled={busy}
                    placeholder="本节教学意图（生成时作为该节核心任务）"
                    onFocus={() => {
                      focusValue.current = p.intent;
                    }}
                    onBlur={() => commitEdit(p.intent)}
                    onChange={(e) => updateField(i, "intent", e.target.value)}
                    className="w-full rounded-lg border border-black/10 px-2.5 py-1.5 text-xs text-ink-600 focus:border-primary-300 focus:outline-none disabled:bg-canvas-50"
                  />
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1.5">
                  <span className="whitespace-nowrap text-[11px] text-ink-400">
                    {p.para && p.para.length > 0 ? `第 ${p.para.join("、")} 段` : "—"}
                  </span>
                  <button
                    onClick={() => deletePage(i)}
                    disabled={busy || locked}
                    title={locked ? "封面/总结节不可删除" : "删除此节"}
                    className="text-sm text-ink-300 transition-colors hover:text-red-500 disabled:opacity-30 disabled:hover:text-ink-300"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </Fragment>
          );
        })}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <select
          value={addKind}
          onChange={(e) => setAddKind(e.target.value)}
          disabled={busy}
          className="rounded-xl border border-black/10 bg-white px-3 py-2 text-sm text-ink-800 focus:border-primary-300 focus:outline-none disabled:opacity-50"
        >
          {ADDABLE_KINDS.map((k) => (
            <option key={k} value={k}>
              {KIND_LABELS[k]}
            </option>
          ))}
        </select>
        <button
          onClick={addPage}
          disabled={busy}
          className="btn-secondary rounded-xl px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          + 添加节
        </button>
        <span className="text-xs text-ink-400">
          新节插入到总结节之前；章节上限 {MAX_CHAPTERS} 章、每章 ≤{MAX_SECTIONS_PER_CHAPTER} 节（超出时生成自动拆并）
        </span>
      </div>
    </div>
  );
}
