"use client";

import { ReactNode } from "react";
import { glossary } from "@/lib/glossary";

interface TermTooltipProps {
  term: string;
  children?: ReactNode;
  /** 显示位置：默认上方 */
  side?: "top" | "bottom";
}

/**
 * 术语 Tooltip：hover / focus 触发，CSS-only 无需 state
 *
 * 内容来自 glossary 字典。若 term 不在字典中，则原样渲染 children。
 *
 * 参考设计：Linear / Stripe Dashboard 的 info icon tooltip
 */
export default function TermTooltip({ term, children, side = "top" }: TermTooltipProps) {
  const entry = glossary[term];
  if (!entry) {
    return <>{children || term}</>;
  }

  return (
    <span className="relative inline-flex items-center group align-baseline">
      <span
        tabIndex={0}
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

      {/* Tooltip */}
      <span
        role="tooltip"
        className={`absolute ${side === "top" ? "bottom-full mb-2" : "top-full mt-2"} left-1/2 -translate-x-1/2 w-64 max-w-[80vw] p-3 rounded-xl dropdown-surface text-left opacity-0 invisible scale-95 pointer-events-none transition-all duration-150 group-hover:opacity-100 group-hover:visible group-hover:scale-100 group-focus-within:opacity-100 group-focus-within:visible group-focus-within:scale-100 z-50`}
      >
        <span className="block text-xs font-semibold text-ink-900 mb-1">{term}</span>
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
