"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  KnowledgeDocument,
  JobStatus,
  listKnowledgeDocuments,
  uploadKnowledgeFile,
  getJobStatus,
  deleteKnowledgeDocument,
} from "@/lib/knowledge";
import DocumentProcessingStatus from "./DocumentProcessingStatus";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const MAX_FILE_SIZE = 20 * 1024 * 1024;

function formatTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("zh-CN", { hour12: false });
}

export default function KnowledgeUploadPanel() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [activeJobs, setActiveJobs] = useState<JobStatus[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await listKnowledgeDocuments("private");
      setDocuments(docs);
    } catch {
      // 列表加载失败静默处理，避免打断上传流程
    }
  }, []);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  // 轮询进行中的任务
  useEffect(() => {
    const pending = activeJobs.filter(
      (j) => j.stage !== "done" && j.stage !== "error"
    );
    if (pending.length === 0) return;

    const timer = setInterval(async () => {
      try {
        const results = await Promise.all(
          pending.map((j) => getJobStatus(j.id))
        );
        setActiveJobs((prev) =>
          prev.map((job) => results.find((r) => r.id === job.id) ?? job)
        );
        if (results.some((r) => r.stage === "done" || r.stage === "error")) {
          void refreshDocuments();
          setActiveJobs((prev) =>
            prev.filter((j) => j.stage !== "done" && j.stage !== "error")
          );
        }
      } catch {
        // 轮询失败静默，继续下一轮
      }
    }, 2000);

    return () => clearInterval(timer);
  }, [activeJobs, refreshDocuments]);

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const file = Array.from(files)[0];
    if (!file) return;
    setError(null);

    const ext = "." + (file.name.split(".").pop() ?? "").toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setError(`不支持的文件格式：${ext || "未知"}，请上传 PDF / DOCX / TXT`);
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("文件过大，请压缩或分段上传（上限 20MB）");
      return;
    }

    try {
      const res = await uploadKnowledgeFile(file);
      setActiveJobs((prev) => [
        ...prev,
        {
          id: res.document_id,
          status: "queued",
          stage: "received",
          progress: null,
          result: null,
          error: null,
          error_code: null,
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "上传失败，请稍后重试");
    }
  }, []);

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      await deleteKnowledgeDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败，请稍后重试");
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };
  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) void handleFiles(e.dataTransfer.files);
  };

  const hasActiveJobs = activeJobs.length > 0;

  return (
    <div className="space-y-6">
      {/* 拖拽上传区 */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-colors ${
          dragOver
            ? "border-primary-400 bg-primary-50"
            : "border-black/10 bg-white/60 hover:border-primary-300 hover:bg-canvas-50"
        }`}
      >
        <div className="text-3xl">📎</div>
        <p className="mt-2 text-sm font-medium text-ink-700">
          拖拽文件到此处，或点击上传
        </p>
        <p className="mt-1 text-xs text-ink-400">
          支持 PDF / DOCX / TXT，单文件不超过 20MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => {
            if (e.target.files) void handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          <span className="mt-0.5 shrink-0">⚠</span>
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            className="shrink-0 text-rose-400 hover:text-rose-600"
          >
            ✕
          </button>
        </div>
      )}

      {/* 进行中任务 */}
      {hasActiveJobs && (
        <div className="space-y-2">
          <div className="section-title">处理中</div>
          {activeJobs.map((job) => (
            <div
              key={job.id}
              className="archive-card p-4"
            >
              <DocumentProcessingStatus job={job} />
            </div>
          ))}
        </div>
      )}

      {/* 已入库文件列表 */}
      <div className="space-y-2">
        <div className="section-title">我的资料（{documents.length}）</div>
        {documents.length === 0 ? (
          <div className="rounded-2xl border border-black/5 bg-white/50 p-8 text-center">
            <p className="text-sm text-ink-400">
              暂无资料，上传你的第一份教学资料吧
            </p>
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              className="archive-card flex items-center gap-3 p-4"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-ink-900">
                  {doc.title}
                </div>
                <div className="mt-0.5 text-xs text-ink-400">
                  {formatTime(doc.created_at) || "未知时间"} · 已入库
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium text-rose-600 transition-colors hover:bg-rose-50"
              >
                删除
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
