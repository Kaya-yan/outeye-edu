"use client";

import { useState } from "react";
import type { VeChainNode, VeTarget } from "./rpc";

function rgbToHex(rgb: string): string {
  const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
  if (!m) return "#ffffff";
  return (
    "#" +
    [1, 2, 3]
      .map((i) => Number(m[i]).toString(16).padStart(2, "0"))
      .join("")
  );
}

function isTransparent(rgb: string): boolean {
  const m = rgb.match(/rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*0(?:\.0+)?\s*\)/);
  return !!m;
}

export default function Inspector({
  target,
  patchValue,
  onStyleChange,
  onStartTextEdit,
  onImageReplace,
  onSelectChain,
  onClose,
}: {
  target: VeTarget;
  patchValue: (prop: string) => string | undefined;
  onStyleChange: (prop: string, value: string | null) => void;
  onStartTextEdit: (selector: string) => void;
  onImageReplace: (selector: string, src: string) => void;
  onSelectChain: (node: VeChainNode) => void;
  onClose: () => void;
}) {
  const s = target.styles;
  const fontSize = patchValue("font-size") || s.fontSize;
  const [sizeText, setSizeText] = useState<string>(
    String(parseFloat(fontSize) || 16)
  );

  const colorVal = patchValue("color") || rgbToHex(s.color);
  const bgVal =
    patchValue("background-color") ||
    (isTransparent(s.background) ? "#ffffff" : rgbToHex(s.background));
  const bgTransparent = !patchValue("background-color") && isTransparent(s.background);
  const alignVal = patchValue("text-align") || s.textAlign;
  const weightVal = patchValue("font-weight") || s.fontWeight;
  const hidden = patchValue("display") === "none";

  const commitSize = () => {
    const n = parseFloat(sizeText);
    if (!Number.isNaN(n) && n >= 8 && n <= 96) onStyleChange("font-size", `${n}px`);
  };

  return (
    <aside className="absolute right-4 top-4 z-30 w-80 max-h-[calc(100%-2rem)] overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-xl">
      <div className="sticky top-0 bg-white flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="rounded bg-blue-600 px-2 py-0.5 text-[11px] font-semibold text-white">{target.tag}</span>
          {target.component && <span className="truncate text-[11px] text-slate-500">{target.component}</span>}
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
                    isLeaf ? "bg-blue-50 text-blue-700" : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
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

      <div className="px-4 py-3 border-b border-slate-100 space-y-3">
        <div className="text-[10px] uppercase tracking-widest text-slate-400">样式调整</div>

        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-slate-500 flex-shrink-0">字号</span>
          <div className="flex items-center gap-1">
            <input
              type="number"
              min={8}
              max={96}
              value={sizeText}
              onChange={(e) => setSizeText(e.target.value)}
              onBlur={commitSize}
              onKeyDown={(e) => {
                if (e.key === "Enter") (e.target as HTMLInputElement).blur();
              }}
              className="w-16 rounded border border-slate-200 px-2 py-1 text-xs text-slate-700 focus:border-blue-500 focus:outline-none"
            />
            <span className="text-xs text-slate-400">px</span>
          </div>
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-slate-500 flex-shrink-0">字重</span>
          <div className="flex rounded border border-slate-200 overflow-hidden">
            {[["400", "正常"], ["700", "加粗"]].map(([v, label]) => (
              <button
                key={v}
                onClick={() => onStyleChange("font-weight", weightVal === v ? null : v)}
                className={`px-2.5 py-1 text-xs transition-colors ${
                  weightVal === v ? "bg-blue-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-slate-500 flex-shrink-0">文字颜色</span>
          <input
            type="color"
            value={colorVal}
            onChange={(e) => onStyleChange("color", e.target.value)}
            className="h-7 w-12 cursor-pointer rounded border border-slate-200 bg-white p-0.5"
          />
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-slate-500 flex-shrink-0">背景颜色</span>
          <div className="flex items-center gap-1.5">
            {bgTransparent && <span className="text-[10px] text-slate-400">当前透明</span>}
            <input
              type="color"
              value={bgVal}
              onChange={(e) => onStyleChange("background-color", e.target.value)}
              className="h-7 w-12 cursor-pointer rounded border border-slate-200 bg-white p-0.5"
            />
          </div>
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-slate-500 flex-shrink-0">对齐</span>
          <div className="flex rounded border border-slate-200 overflow-hidden">
            {[["left", "左"], ["center", "中"], ["right", "右"]].map(([v, label]) => (
              <button
                key={v}
                onClick={() => onStyleChange("text-align", alignVal === v ? null : v)}
                className={`px-2.5 py-1 text-xs transition-colors ${
                  alignVal === v ? "bg-blue-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => onStyleChange("display", hidden ? null : "none")}
          className={`w-full rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            hidden ? "bg-amber-50 text-amber-700 border border-amber-200" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          {hidden ? "恢复显示该元素" : "隐藏该元素"}
        </button>

        {target.childCount === 0 && target.tag !== "img" && (
          <button
            onClick={() => onStartTextEdit(target.selector)}
            className="w-full rounded-lg px-3 py-1.5 text-xs font-medium bg-slate-100 text-slate-600 hover:bg-slate-200"
          >
            编辑文本（或双击该元素）
          </button>
        )}
      </div>

      {target.tag === "img" && (
        <div className="px-4 py-3 border-b border-slate-100 space-y-2.5">
          <div className="text-[10px] uppercase tracking-widest text-slate-400">图片</div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">
            {target.src.startsWith("data:") ? (
              <span className="text-[11px] text-slate-500">内嵌图片（base64）</span>
            ) : (
              <span className="text-[11px] text-slate-500 break-all line-clamp-2">{target.src || "无 src"}</span>
            )}
          </div>
          <label className="block w-full cursor-pointer rounded-lg bg-blue-600 px-3 py-1.5 text-center text-xs font-medium text-white hover:bg-blue-700">
            上传图片替换
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                if (f.size > 2 * 1024 * 1024) {
                  alert("图片过大（上限 2MB），请压缩后再上传");
                  e.target.value = "";
                  return;
                }
                const reader = new FileReader();
                reader.onload = () => onImageReplace(target.selector, String(reader.result));
                reader.readAsDataURL(f);
                e.target.value = "";
              }}
            />
          </label>
          <div className="flex gap-1.5">
            <input
              type="text"
              placeholder="或输入图片 URL"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  const v = (e.target as HTMLInputElement).value.trim();
                  if (v) onImageReplace(target.selector, v);
                }
              }}
              className="flex-1 min-w-0 rounded border border-slate-200 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>
      )}

      {target.text && (
        <div className="px-4 py-3">
          <div className="text-[10px] uppercase tracking-widest text-slate-400 mb-2">文本</div>
          <p className="text-xs text-slate-600 leading-5 line-clamp-3">{target.text}</p>
        </div>
      )}
    </aside>
  );
}
