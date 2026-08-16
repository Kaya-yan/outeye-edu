"use client";

import { apiGet, apiUpload, apiDelete } from "@/lib/api";

export type JobStage =
  | "received"
  | "parsing"
  | "chunking"
  | "embedding"
  | "done"
  | "error";

export interface KnowledgeDocument {
  id: string;
  title: string;
  source: string;
  doc_type: string;
  tags: string[];
  summary: string;
  status: string;
  created_at: string | null;
}

export interface JobStatus {
  id: string;
  status: string;
  stage: JobStage;
  progress: { processed_chunks: number; total_chunks: number } | null;
  result: Record<string, unknown> | null;
  error: string | null;
  error_code: string | null;
}

export const ERROR_CODE_MESSAGES: Record<string, string> = {
  SCANNED_PDF: "扫描件无法自动解析，请上传可编辑文档或手动粘贴文本",
  FILE_TOO_LARGE: "文件过大，请压缩或分段上传（上限 20MB）",
  WORD_PARSE_FAILED: "文件解析失败，请检查格式或另存为 DOCX/PDF",
  TEXT_ENCODING_FAILED: "文本编码错误，请转换为 UTF-8 后重试",
  EMBEDDING_WAITING: "模型加载中，请稍后刷新",
  EMBEDDING_FAILED: "向量化失败，请稍后重试",
};

export const STAGE_LABELS: Record<JobStage, string> = {
  received: "已接收",
  parsing: "解析中",
  chunking: "分块中",
  embedding: "向量化中",
  done: "已入库",
  error: "处理失败",
};

export const DOC_TYPE_LABELS: Record<string, string> = {
  theory: "理论",
  strategy: "策略",
  case: "案例",
  document: "文档",
};

export const listKnowledgeDocuments = (scope: "system" | "private") =>
  apiGet<KnowledgeDocument[]>(`/knowledge/documents?scope=${scope}`);

export const uploadKnowledgeFile = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return apiUpload<{ document_id: string; status: string }>(
    "/knowledge/upload",
    fd
  );
};

export const getJobStatus = (id: string) =>
  apiGet<JobStatus>(`/rag/jobs/${id}`);

export const deleteKnowledgeDocument = (id: string) =>
  apiDelete<{ success: boolean }>(`/knowledge/documents/${id}`);

export const getRagStatus = () =>
  apiGet<{ status: "ready" | "loading" }>("/rag/status");
