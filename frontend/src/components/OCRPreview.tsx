"use client";

import { useState } from "react";

interface OCRPreviewProps {
  text: string;
  confidence: number;
  engine: string;
  onConfirm: (text: string) => void;
  onRetry: (engine: "aliyun" | "llm") => void;
  loading?: boolean;
}

export default function OCRPreview({
  text,
  confidence,
  engine,
  onConfirm,
  onRetry,
  loading,
}: OCRPreviewProps) {
  const [editedText, setEditedText] = useState(text);

  const engineLabel = engine === "aliyun" ? "阿里云 OCR" : "LLM 视觉";
  const confidenceColor =
    confidence >= 0.8 ? "text-green-600" : confidence >= 0.5 ? "text-yellow-600" : "text-red-600";

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">📷</span>
          <span className="text-sm font-medium text-gray-700">OCR 识别结果</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{engineLabel}</span>
          <span className={`text-xs ${confidenceColor}`}>
            置信度 {(confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* 识别文本（可编辑） */}
      <textarea
        value={editedText}
        onChange={(e) => setEditedText(e.target.value)}
        className="w-full h-40 px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none resize-y"
        placeholder="识别结果将显示在这里..."
      />

      {/* 操作按钮 */}
      <div className="flex items-center gap-2 mt-3">
        <button
          onClick={() => onConfirm(editedText)}
          disabled={!editedText.trim()}
          className="px-4 py-1.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
        >
          确认使用
        </button>
        <button
          onClick={() => onRetry("aliyun")}
          disabled={loading}
          className="px-4 py-1.5 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          {loading ? "识别中..." : "重新识别"}
        </button>
        <button
          onClick={() => onRetry(engine === "aliyun" ? "llm" : "aliyun")}
          disabled={loading}
          className="px-4 py-1.5 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          切换引擎（{engine === "aliyun" ? "LLM" : "阿里云"}）
        </button>
      </div>
    </div>
  );
}
