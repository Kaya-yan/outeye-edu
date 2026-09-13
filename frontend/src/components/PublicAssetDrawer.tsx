"use client";

import { useEffect, useState } from "react";
import { getPublicKnowledgeDetail, type PublicKnowledgeItem } from "@/lib/knowledge";

/**
 * 公共资料详情抽屉（任务F3）：点开知识条目看完整内容——标题、类别、来源、更新时间、正文。
 * 「内容可追溯、知识权威可信」的直接证据，交互上做足仪式感：右侧滑入 + 遮罩 + Esc 关闭。
 */
export default function PublicAssetDrawer({
  item,
  onClose,
}: {
  item: PublicKnowledgeItem;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await getPublicKnowledgeDetail(item.id);
        if (!cancelled) setDetail(d.detail);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "详情加载失败");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [item.id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const paragraphs = (detail || "").split("\n").filter((p) => p.trim());

  return (
    <div className="fixed inset-0 z-[80]" role="dialog" aria-modal="true" aria-label={item.title}>
      <div
        className="absolute inset-0 bg-ink-900/30 backdrop-blur-[2px] transition-opacity"
        onClick={onClose}
      />
      <aside className="absolute right-0 top-0 h-full w-full max-w-xl overflow-y-auto bg-white shadow-2xl sm:rounded-l-3xl">
        <div className="sticky top-0 z-10 border-b border-black/5 bg-white/95 px-6 py-5 backdrop-blur sm:px-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-sage-100 border border-sage-200 px-2.5 py-0.5 text-[11px] font-medium text-ink-700">
                  {item.category}
                </span>
                <span className="rounded-full bg-primary-100 border border-primary-200 px-2.5 py-0.5 text-[11px] font-semibold text-primary-700">
                  {item.badge}
                </span>
                <span className="text-[11px] text-ink-400">{item.source}</span>
                {item.created_at && (
                  <span className="text-[11px] text-ink-300">
                    {new Date(item.created_at).toLocaleDateString("zh-CN")}
                  </span>
                )}
              </div>
              <h2 className="mt-2.5 text-xl font-semibold text-ink-900">{item.title}</h2>
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

        <div className="px-6 py-6 sm:px-8">
          {error && (
            <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </p>
          )}
          {!error && detail === null && (
            <p className="py-8 text-center text-sm text-ink-400">正文加载中…</p>
          )}
          {detail === "" && !error && (
            <p className="py-8 text-center text-sm text-ink-400">该条目暂无正文</p>
          )}
          {paragraphs.map((p, i) => (
            <p key={i} className="mb-3.5 text-sm leading-7 text-ink-700 whitespace-pre-line">
              {p}
            </p>
          ))}
        </div>
      </aside>
    </div>
  );
}
