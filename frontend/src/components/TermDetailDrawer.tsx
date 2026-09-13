"use client";

import { useEffect } from "react";
import type { GlossaryEntry } from "@/lib/glossary";

/**
 * 术语完整解读抽屉（任务G2）：白盒分析页点击术语后右侧滑入，
 * 展示术语全称 / 一句话解释 / 本文数值解读 / 教学提示。
 */
export default function TermDetailDrawer({
  term,
  entry,
  onClose,
}: {
  term: string;
  entry: GlossaryEntry | null;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!entry) return null;

  return (
    <div className="fixed inset-0 z-[85]" role="dialog" aria-modal="true" aria-label={entry.name || term}>
      <div className="absolute inset-0 bg-ink-900/30 backdrop-blur-[2px] transition-opacity" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full w-full max-w-md overflow-y-auto bg-white shadow-2xl sm:rounded-l-3xl">
        <div className="sticky top-0 z-10 border-b border-black/5 bg-white/95 px-6 py-5 backdrop-blur sm:px-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-ink-400">指标解读</div>
              <h2 className="mt-1.5 text-xl font-semibold text-ink-900">{entry.name || term}</h2>
            </div>
            <button
              onClick={onClose}
              aria-label="关闭"
              className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-black/10 text-ink-500 transition-colors hover:bg-canvas-100"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="space-y-5 px-6 py-6 sm:px-8">
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-400">是什么</h3>
            <p className="mt-2 text-sm leading-7 text-ink-700">{entry.definition}</p>
          </section>
          {entry.interpretation && (
            <section className="rounded-2xl border border-primary-100 bg-primary-50/60 px-4 py-3.5">
              <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-600">本文解读</h3>
              <p className="mt-1.5 text-sm leading-7 text-ink-800">{entry.interpretation}</p>
            </section>
          )}
          {entry.teaching && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-400">对教学意味着什么</h3>
              <p className="mt-2 text-sm leading-7 text-ink-700">{entry.teaching}</p>
            </section>
          )}
          <p className="border-t border-black/5 pt-4 text-[11px] leading-5 text-ink-400">
            解读由白盒分析按本篇课文数值实时生成，悬停术语可随时快速查看。
          </p>
        </div>
      </aside>
    </div>
  );
}
