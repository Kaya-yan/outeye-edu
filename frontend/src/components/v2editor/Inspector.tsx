"use client";

import type { VeChainNode, VeTarget } from "./rpc";

export default function Inspector({
  target,
  onSelectChain,
  onClose,
}: {
  target: VeTarget;
  onSelectChain: (node: VeChainNode) => void;
  onClose: () => void;
}) {
  const s = target.styles;
  const rows: Array<[string, string]> = [
    ["尺寸", `${Math.round(target.rect.w)} × ${Math.round(target.rect.h)} px`],
    ["字体", `${s.fontSize} / ${s.fontWeight}`],
    ["颜色", s.color],
    ["背景", s.background === "rgba(0, 0, 0, 0)" ? "透明" : s.background],
    ["对齐", s.textAlign],
    ["内边距", s.padding],
  ];

  return (
    <aside className="absolute right-4 top-4 z-30 w-80 rounded-xl border border-slate-200 bg-white shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="rounded bg-blue-600 px-2 py-0.5 text-[11px] font-semibold text-white">{target.tag}</span>
          {target.component && (
            <span className="truncate text-[11px] text-slate-500">{target.component}</span>
          )}
          {target.page && (
            <span className="text-[11px] text-slate-400">
              第 {target.page} 页{target.pageTitle ? ` · ${target.pageTitle}` : ""}
            </span>
          )}
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-sm leading-none" aria-label="关闭">
          ✕
        </button>
      </div>

      <div className="px-4 py-3 border-b border-slate-100">
        <div className="text-[10px] uppercase tracking-widest text-slate-400 mb-2">层级</div>
        <div className="flex flex-wrap items-center gap-1">
          {target.chain.map((node, i) => {
            const isLeaf = i === target.chain.length - 1;
            return (
              <span key={i} className="flex items-center gap-1">
                <button
                  onClick={() => onSelectChain(node)}
                  className={`rounded px-1.5 py-0.5 text-[11px] font-mono transition-colors ${
                    isLeaf
                      ? "bg-blue-50 text-blue-700"
                      : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                  }`}
                >
                  {node.tag}
                  {node.component ? `(${node.component})` : ""}
                </button>
                {i < target.chain.length - 1 && <span className="text-slate-300 text-[10px]">›</span>}
              </span>
            );
          })}
        </div>
      </div>

      {target.text && (
        <div className="px-4 py-3 border-b border-slate-100">
          <div className="text-[10px] uppercase tracking-widest text-slate-400 mb-2">文本</div>
          <p className="text-xs text-slate-600 leading-5 line-clamp-3">{target.text}</p>
        </div>
      )}

      <div className="px-4 py-3">
        <div className="text-[10px] uppercase tracking-widest text-slate-400 mb-2">计算样式</div>
        <dl className="space-y-1.5">
          {rows.map(([k, v]) => (
            <div key={k} className="flex items-start justify-between gap-3 text-xs">
              <dt className="text-slate-400 flex-shrink-0">{k}</dt>
              <dd className="text-slate-700 text-right font-mono break-all">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </aside>
  );
}
