"use client";

import React, { useEffect, useState } from "react";
import KnowledgeUploadPanel from "@/components/KnowledgeUploadPanel";
import { listKnowledgeDocuments, listPublicKnowledge, type PublicKnowledgeItem } from "@/lib/knowledge";

type Tab = "mine" | "public";

export default function MaterialsPage() {
  const [tab, setTab] = useState<Tab>("mine");
  const [publicItems, setPublicItems] = useState<PublicKnowledgeItem[]>([]);
  const [publicLoaded, setPublicLoaded] = useState(false);
  const [publicError, setPublicError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mine = await listKnowledgeDocuments("private");
        if (!cancelled && mine.length === 0) setTab("public");
      } catch {
        // 无法判断时保持默认"我的资料"
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (tab !== "public" || publicLoaded) return;
    (async () => {
      try {
        const items = await listPublicKnowledge();
        setPublicItems(items);
        setPublicLoaded(true);
      } catch (e: unknown) {
        setPublicError(e instanceof Error ? e.message : "公共资料加载失败");
      }
    })();
  }, [tab, publicLoaded]);

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="mx-auto mb-6 max-w-4xl">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900 sm:text-3xl">资料中心</h1>
        <p className="mt-2 text-sm text-ink-500">
          我的资料会参与课文分析；公共资料是平台提供的知识资产说明，所有人可见。
        </p>

        <div className="mt-5 inline-flex rounded-2xl border border-black/5 bg-white p-1 shadow-soft">
          <TabButton active={tab === "mine"} onClick={() => setTab("mine")}>
            我的资料
          </TabButton>
          <TabButton active={tab === "public"} onClick={() => setTab("public")}>
            公共资料
          </TabButton>
        </div>
      </header>

      <main className="mx-auto max-w-4xl">
        {tab === "mine" ? (
          <section className="page-surface-strong px-6 py-6 sm:px-8">
            <KnowledgeUploadPanel />
          </section>
        ) : (
          <section className="space-y-3">
            {!publicLoaded && !publicError && (
              <div className="page-surface-strong px-6 py-10 text-center text-sm text-ink-400">
                加载中...
              </div>
            )}
            {publicError && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {publicError}
              </div>
            )}
            {publicItems.map((item) => (
              <article key={item.id} className="page-surface-strong px-6 py-5 sm:px-7">
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
                <h2 className="mt-3 text-lg font-semibold text-ink-900">{item.title}</h2>
                <p className="mt-2 text-sm leading-6 text-ink-500">{item.summary}</p>
              </article>
            ))}
            {publicLoaded && publicItems.length === 0 && (
              <div className="page-surface-strong px-6 py-10 text-center text-sm text-ink-400">
                暂无公共资料
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-xl px-5 py-2 text-sm font-medium transition-colors ${
        active ? "bg-primary-600 text-white shadow-soft" : "text-ink-600 hover:bg-canvas-100"
      }`}
    >
      {children}
    </button>
  );
}
