"use client";

import React, { useEffect, useState } from "react";
import { getRagStatus, listKnowledgeDocuments, KnowledgeDocument } from "@/lib/knowledge";
import KnowledgeDocumentCard from "@/components/KnowledgeDocumentCard";
import KnowledgeUploadPanel from "@/components/KnowledgeUploadPanel";

type Tab = "system" | "mine";

export default function KnowledgePage() {
  const [tab, setTab] = useState<Tab>("system");
  const [systemStatus, setSystemStatus] = useState<"ready" | "loading">("loading");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getRagStatus()
      .then((r) => setSystemStatus(r.status))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (tab !== "system") return;
    setLoading(true);
    listKnowledgeDocuments("system")
      .then((docs) => setDocuments(docs))
      .catch(() => setDocuments([]))
      .finally(() => setLoading(false));
  }, [tab]);

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="brand-surface mx-auto mb-6 max-w-7xl px-6 py-7 sm:px-8 sm:py-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="section-title mb-2">Knowledge Repository</div>
            <h1 className="text-3xl font-semibold tracking-tight text-ink-900 sm:text-4xl">
              知识库
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-ink-500 sm:text-base">
              查看系统预置的教学理论，或上传并管理你的个人教学资料。
            </p>
          </div>

          <div className="self-start lg:self-auto">
            {systemStatus === "ready" ? (
              <span className="inline-flex items-center gap-2 rounded-full border border-sage-200 bg-sage-100 px-4 py-2 text-xs font-medium text-sage-800">
                <span className="h-2 w-2 rounded-full bg-sage-500" />
                系统就绪
              </span>
            ) : (
              <span className="inline-flex items-center gap-2 rounded-full border border-accent-200 bg-accent-50 px-4 py-2 text-xs font-medium text-accent-800">
                <span className="h-2 w-2 animate-pulse rounded-full bg-accent-500" />
                模型加载中，约需 60 秒
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6">
        {/* 标签页切换 */}
        <div className="inline-flex rounded-2xl border border-black/5 bg-white p-1 shadow-soft">
          <button
            onClick={() => setTab("system")}
            className={`rounded-xl px-5 py-2 text-sm font-medium transition-colors ${
              tab === "system"
                ? "bg-primary-500 text-ink-900"
                : "text-ink-500 hover:bg-canvas-100"
            }`}
          >
            系统公共资源
          </button>
          <button
            onClick={() => setTab("mine")}
            className={`rounded-xl px-5 py-2 text-sm font-medium transition-colors ${
              tab === "mine"
                ? "bg-primary-500 text-ink-900"
                : "text-ink-500 hover:bg-canvas-100"
            }`}
          >
            我的资料
          </button>
        </div>

        {tab === "system" ? (
          <section className="archive-surface p-6 animate-fade-in">
            <div className="mb-4 flex items-baseline justify-between">
              <div>
                <div className="section-title mb-1">System Resources</div>
                <h2 className="text-xl font-semibold text-ink-900">
                  系统预置知识
                </h2>
              </div>
              <span className="text-sm text-ink-400">{documents.length} 篇</span>
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="animate-spin rounded-full border-2 border-primary-200 border-t-primary-600 h-10 w-10" />
                <p className="mt-4 text-sm text-ink-400">加载中...</p>
              </div>
            ) : documents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <p className="text-sm text-ink-400">暂无系统预置知识</p>
              </div>
            ) : (
              <div className="space-y-3">
                {documents.map((doc) => (
                  <KnowledgeDocumentCard key={doc.id} doc={doc} />
                ))}
              </div>
            )}
          </section>
        ) : (
          <section className="archive-surface p-6 animate-fade-in">
            <div className="mb-4">
              <div className="section-title mb-1">My Materials</div>
              <h2 className="text-xl font-semibold text-ink-900">我的资料</h2>
            </div>
            <KnowledgeUploadPanel />
          </section>
        )}
      </main>
    </div>
  );
}
