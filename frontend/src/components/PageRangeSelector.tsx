"use client";

import { useState, useMemo } from "react";

interface PageRangeSelectorProps {
  filename: string;
  totalPages: number;
  onConfirm: (pageFrom: number, pageTo: number) => void;
  loading?: boolean;
}

export default function PageRangeSelector({
  filename,
  totalPages,
  onConfirm,
  loading,
}: PageRangeSelectorProps) {
  const [mode, setMode] = useState<"all" | "custom">("all");
  const [pageFrom, setPageFrom] = useState(1);
  const [pageTo, setPageTo] = useState(totalPages);

  const isValid = pageFrom >= 1 && pageTo <= totalPages && pageFrom <= pageTo;
  const selectedCount = mode === "all" ? totalPages : pageTo - pageFrom + 1;

  const previewBlocks = useMemo(() => {
    const blocks = [];
    const maxShow = 30; // 最多显示 30 个小方块
    const step = totalPages > maxShow ? Math.ceil(totalPages / maxShow) : 1;

    for (let i = 1; i <= totalPages; i += step) {
      const end = Math.min(i + step - 1, totalPages);
      const isStart = i === 1;
      const isEnd = end === totalPages;
      const isIncluded =
        mode === "all" || (i >= pageFrom && end <= pageTo);

      blocks.push(
        <div
          key={i}
          className={`h-3 rounded-sm transition-colors ${
            isIncluded
              ? "bg-primary"
              : "bg-gray-200"
          }`}
          style={{ width: `${Math.max(8, 100 / Math.min(totalPages / step, maxShow))}%` }}
          title={`第 ${i}${i !== end ? `-${end}` : ""} 页`}
        />
      );
    }
    return blocks;
  }, [totalPages, mode, pageFrom, pageTo]);

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm text-gray-500">📄</span>
        <span className="text-sm font-medium text-gray-700">{filename}</span>
        <span className="text-xs text-gray-400">共 {totalPages} 页</span>
      </div>

      {/* 范围模式选择 */}
      <div className="flex items-center gap-3 mb-3">
        <label className="text-sm text-gray-600">分析范围：</label>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as "all" | "custom")}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
        >
          <option value="all">全部页面</option>
          <option value="custom">自定义范围</option>
        </select>
      </div>

      {/* 自定义范围 */}
      {mode === "custom" && (
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm text-gray-600">从</span>
          <select
            value={pageFrom}
            onChange={(e) => {
              const v = Number(e.target.value);
              setPageFrom(v);
              if (v > pageTo) setPageTo(v);
            }}
            className="px-2 py-1 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
          >
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n} disabled={n > pageTo}>
                {n}
              </option>
            ))}
          </select>
          <span className="text-sm text-gray-600">到</span>
          <select
            value={pageTo}
            onChange={(e) => {
              const v = Number(e.target.value);
              setPageTo(v);
              if (v < pageFrom) setPageFrom(v);
            }}
            className="px-2 py-1 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
          >
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n} disabled={n < pageFrom}>
                {n}
              </option>
            ))}
          </select>
          <span className="text-sm text-gray-600">页</span>
        </div>
      )}

      {/* 页面预览条 */}
      <div className="flex gap-0.5 mb-3 flex-wrap">{previewBlocks}</div>

      {/* 提示和确认 */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">
          将提取第 {mode === "all" ? `1-${totalPages}` : `${pageFrom}-${pageTo}`} 页的内容（共 {selectedCount} 页）
        </span>
        <button
          onClick={() => onConfirm(mode === "all" ? 1 : pageFrom, mode === "all" ? totalPages : pageTo)}
          disabled={loading || !isValid}
          className="px-4 py-1.5 text-sm font-medium text-white bg-primary rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? "解析中..." : "确认提取"}
        </button>
      </div>
    </div>
  );
}
