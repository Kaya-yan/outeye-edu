"use client";

import { useState } from "react";
import { KnowledgeDocument, DOC_TYPE_LABELS } from "@/lib/knowledge";

export default function KnowledgeDocumentCard({
  doc,
}: {
  doc: KnowledgeDocument;
}) {
  const [open, setOpen] = useState(false);
  const typeLabel = DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type;

  return (
    <div
      className="archive-card cursor-pointer p-5 transition-all duration-200 hover:-translate-y-0.5"
      onClick={() => setOpen((v) => !v)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-base font-semibold text-ink-900">
              {doc.title}
            </h3>
            <span className="inline-flex shrink-0 items-center rounded-full border border-primary-200 bg-primary-100 px-2 py-0.5 text-xs font-medium text-ink-700">
              {typeLabel}
            </span>
          </div>
          <p className="mt-1 text-xs text-ink-400">
            来源：{doc.source === "system_seed" ? "系统预置" : doc.source}
          </p>
          {doc.tags && doc.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {doc.tags.map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center rounded-full border border-black/5 bg-canvas-100 px-2 py-0.5 text-xs text-ink-500"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
        <span className="shrink-0 text-xs text-ink-400">
          {open ? "收起 ▲" : "展开 ▼"}
        </span>
      </div>

      {open && (
        <p className="mt-3 border-t border-black/5 pt-3 text-sm leading-relaxed text-ink-600">
          {doc.summary || "暂无摘要"}
        </p>
      )}
    </div>
  );
}
