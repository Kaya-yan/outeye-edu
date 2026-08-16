"use client";

import { useState } from "react";
import { TeachingContext } from "@/lib/analysis";

const COURSE_TYPES = ["精读", "读写", "翻译", "听力", "口语"];
const CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];

export default function TeachingContextPanel({
  initialStudentLevel,
  onConfirm,
  onCancel,
  loading,
}: {
  initialStudentLevel: string;
  onConfirm: (ctx: TeachingContext) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [courseType, setCourseType] = useState("精读");
  const [durationMinutes, setDurationMinutes] = useState(90);
  const [classSize, setClassSize] = useState(30);
  const [studentLevel, setStudentLevel] = useState(initialStudentLevel || "B1");
  const [mode, setMode] = useState<"basic" | "enhanced">("enhanced");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-3xl border border-white/40 bg-white p-6 shadow-elevated animate-scale-in">
        <div className="mb-5">
          <div className="section-title mb-1">Teaching Context</div>
          <h2 className="text-xl font-semibold text-ink-900">教学情境确认</h2>
          <p className="mt-1 text-sm text-ink-500">
            确认教学情境后，系统将生成教学设计。
          </p>
        </div>

        <div className="space-y-4">
          {/* 课型 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">课型</label>
            <div className="flex flex-wrap gap-2">
              {COURSE_TYPES.map((c) => (
                <button
                  key={c}
                  onClick={() => setCourseType(c)}
                  className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                    courseType === c
                      ? "border-primary-500 bg-primary-100 text-ink-900"
                      : "border-black/10 bg-white text-ink-600 hover:border-primary-300"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {/* 时长 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">
              时长（分钟）
            </label>
            <input
              type="number"
              value={durationMinutes}
              min={5}
              max={180}
              onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 90)}
              className="morandi-input"
            />
          </div>

          {/* 班级人数 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">班级人数</label>
            <input
              type="number"
              value={classSize}
              min={1}
              max={200}
              onChange={(e) => setClassSize(parseInt(e.target.value) || 30)}
              className="morandi-input"
            />
          </div>

          {/* 学生水平 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">学生水平</label>
            <div className="flex flex-wrap gap-2">
              {CEFR_LEVELS.map((l) => (
                <button
                  key={l}
                  onClick={() => setStudentLevel(l)}
                  className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                    studentLevel === l
                      ? "border-primary-500 bg-primary-100 text-ink-900"
                      : "border-black/10 bg-white text-ink-600 hover:border-primary-300"
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>

          {/* 生成模式 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">生成模式</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setMode("basic")}
                className={`rounded-xl border p-3 text-left transition-colors ${
                  mode === "basic"
                    ? "border-primary-500 bg-primary-100"
                    : "border-black/10 bg-white hover:border-primary-300"
                }`}
              >
                <div className="text-sm font-medium text-ink-900">基础模式</div>
                <div className="mt-0.5 text-xs text-ink-500">快速生成基础教案</div>
              </button>
              <button
                onClick={() => setMode("enhanced")}
                className={`rounded-xl border p-3 text-left transition-colors ${
                  mode === "enhanced"
                    ? "border-primary-500 bg-primary-100"
                    : "border-black/10 bg-white hover:border-primary-300"
                }`}
              >
                <div className="text-sm font-medium text-ink-900">增强模式</div>
                <div className="mt-0.5 text-xs text-ink-500">含证据引用与教学蓝图</div>
              </button>
            </div>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button onClick={onCancel} className="btn-secondary flex-1">
            取消
          </button>
          <button
            onClick={() =>
              onConfirm({ courseType, durationMinutes, classSize, studentLevel, mode })
            }
            disabled={loading}
            className="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "生成中..." : "生成教学设计"}
          </button>
        </div>
      </div>
    </div>
  );
}
