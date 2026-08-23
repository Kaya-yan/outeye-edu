"use client";

import React from "react";
import KnowledgeUploadPanel from "@/components/KnowledgeUploadPanel";

export default function MaterialsPage() {
  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="mx-auto mb-6 max-w-4xl">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900 sm:text-3xl">我的资料</h1>
        <p className="mt-2 text-sm text-ink-500">上传教学大纲、词表或背景资料，分析课文时会自动参考。</p>
      </header>

      <main className="mx-auto max-w-4xl">
        <section className="page-surface-strong px-6 py-6 sm:px-8">
          <KnowledgeUploadPanel />
        </section>
      </main>
    </div>
  );
}
