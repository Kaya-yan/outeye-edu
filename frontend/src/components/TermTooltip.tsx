"use client";

import { ReactNode, useEffect, useRef, useState } from "react";
import { glossary, GlossaryEntry } from "@/lib/glossary";

interface TermTooltipProps {
  term: string;
  children?: ReactNode;
  /** 显示位置：默认上方 */
  side?: "top" | "bottom";
  /** 整行触发：外层占满父容器宽度，用于卡片标签行等小字号场景 */
  block?: boolean;
  /** 后端术语表条目（含按本文数值实例化的解读）；缺省回退本地字典 */
  entry?: GlossaryEntry;
}

/**
 * 术语 Tooltip：hover / focus / 点按 触发
 *
 * 条目来源优先级：后端 metric_glossary 条目 → 本地 glossary 字典。
 * 点按切换用于触屏（CSS hover 不可靠）；Esc 或失焦关闭。
 * 参考设计：Linear / Stripe Dashboard 的 info icon tooltip
 */
export default function TermTooltip({ term, children, side = "top", block = false, entry: entryOverride }: TermTooltipProps) {
  const entry = entryOverride || glossary[term];
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!entry) {
    return <>{children || term}</>;
  }

  return (
    <span className={`relative items-center group align-baseline ${block ? "flex w-full" : "inline-flex"}`}>
      <span
        ref={triggerRef}
        tabIndex={0}
        role="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((o) => !o);
          }
        }}
        className="cursor-help underline decoration-dotted decoration-ink-300 underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-primary-300 rounded"
      >
        {children || term}
      </span>
      <svg
        className="w-3 h-3 ml-0.5 text-ink-400 inline-block flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l1.5 1.5m0 0l1.5 1.5m-1.5-1.5l-1.5 1.5m1.5-1.5l1.5-1.5" />
      </svg>

      {/* Tooltip：层级需高于吸顶导航(z-40)与导航下拉(z-50) */}
      <span
        role="tooltip"
        className={`absolute ${side === "top" ? "bottom-full mb-2" : "top-full mt-2"} left-1/2 -translate-x-1/2 w-64 max-w-[80vw] p-3 rounded-xl dropdown-surface text-left opacity-0 invisible scale-95 pointer-events-none transition-all duration-150 group-hover:opacity-100 group-hover:visible group-hover:scale-100 group-focus-within:opacity-100 group-focus-within:visible group-focus-within:scale-100 z-[70] ${open ? "opacity-100 visible scale-100" : ""}`}
      >
        <span className="block text-xs font-semibold text-ink-900 mb-1">{entry.name || term}</span>
        <span className="block text-xs text-ink-700 leading-relaxed">{entry.definition}</span>
        {entry.interpretation && (
          <span className="block mt-1.5 text-[11px] text-ink-500 leading-relaxed">
            <span className="font-semibold text-ink-600">解读：</span>
            {entry.interpretation}
          </span>
        )}
        {entry.teaching && (
          <span className="block mt-1 text-[11px] text-ink-500 leading-relaxed">
            <span className="font-semibold text-ink-600">教学：</span>
            {entry.teaching}
          </span>
        )}
      </span>
    </span>
  );
}
