"use client";

import React, { useRef, useState } from "react";
import { apiPost, apiRequest } from "@/lib/api";

interface RAGResponse {
  answer: string;
  sources: Array<Record<string, any>>;
  confidence: number;
  response_time: number;
  model?: string;
}

type DrawerKey = "query" | "upload" | "guide" | "samples";

export default function ResourcesPage() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [useWiki, setUseWiki] = useState(true);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [activeDrawer, setActiveDrawer] = useState<DrawerKey>("query");
  const [openDrawers, setOpenDrawers] = useState<Record<DrawerKey, boolean>>({
    query: true,
    upload: true,
    guide: true,
    samples: true,
  });

  const queryRef = useRef<HTMLDivElement | null>(null);
  const uploadRef = useRef<HTMLDivElement | null>(null);
  const guideRef = useRef<HTMLDivElement | null>(null);
  const samplesRef = useRef<HTMLDivElement | null>(null);

  const handleQuery = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setActiveDrawer("query");
    try {
      const endpoint = useWiki ? "/rag/query-with-wiki" : "/rag/query";
      const data = await apiPost<RAGResponse>(endpoint, {
        query,
        method: "hybrid",
        top_k: 5,
        use_wiki: useWiki,
      });
      setResponse(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "查询失败");
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;

    setUploadStatus("上传中...");
    setActiveDrawer("upload");
    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      const res = await apiRequest("POST", "/rag/upload-file", undefined, { body: formData, headers: {} });
      if (!res.ok) throw new Error(`上传失败: ${res.status}`);
      const data = await res.json();
      setUploadStatus(`上传成功：${data.message}`);
    } catch (err: unknown) {
      setUploadStatus(err instanceof Error ? `上传失败：${err.message}` : "上传失败");
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "bg-sage-100 text-ink-800 border border-sage-200";
    if (confidence >= 0.5) return "bg-accent-100 text-ink-900 border border-accent-200";
    return "bg-rose-100 text-ink-900 border border-rose-200";
  };

  const sampleQuestions = [
    "Krashen i+1理论如何应用于课文选择？",
    "如何评估课文的认知负荷？",
    "Bloom分类学在教学设计中的应用？",
    "什么是ZPD理论？",
  ];

  const scrollToDrawer = (key: DrawerKey) => {
    setActiveDrawer(key);
    setOpenDrawers((prev) => ({ ...prev, [key]: true }));
    const refMap = {
      query: queryRef,
      upload: uploadRef,
      guide: guideRef,
      samples: samplesRef,
    };
    refMap[key].current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const toggleDrawer = (key: DrawerKey) => {
    setOpenDrawers((prev) => ({ ...prev, [key]: !prev[key] }));
    setActiveDrawer(key);
  };

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="max-w-7xl mx-auto brand-surface px-6 py-7 sm:px-8 sm:py-8 mb-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="section-title mb-2">Archive Resources</div>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-ink-900">资源库</h1>
            <p className="text-sm sm:text-base text-ink-500 mt-3 max-w-2xl leading-7">
              在档案式资源系统中搜索、上传与整理教学资料，让检索问答、文档入库和常见问题都能被快速定位。
            </p>
          </div>
          <div className="rounded-full bg-canvas-200 px-4 py-2 text-xs font-medium text-ink-600 shadow-soft self-start lg:self-auto">
            Morandi Resource Drawers
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)] gap-8">
        <aside className="space-y-4 lg:sticky lg:top-8 self-start">
          <div className="archive-surface p-5">
            <div className="section-title mb-2">Drawer Index</div>
            <h2 className="text-xl font-semibold text-ink-900">资源抽屉</h2>
            <div className="mt-4 space-y-2">
              {[
                { key: "query", title: "检索问答", hint: "查询与结果" },
                { key: "upload", title: "文档入库", hint: "上传与状态" },
                { key: "guide", title: "使用说明", hint: "检索方法" },
                { key: "samples", title: "热门问题", hint: "快速起步" },
              ].map((item) => (
                <button
                  key={item.key}
                  onClick={() => scrollToDrawer(item.key as DrawerKey)}
                  className={`w-full text-left rounded-2xl px-4 py-3 transition-colors ${
                    activeDrawer === item.key ? "bg-archive-800 text-white" : "bg-white border border-black/5 text-ink-600 hover:bg-canvas-100"
                  }`}
                >
                  <div className="text-sm font-semibold">{item.title}</div>
                  <div className={`text-xs mt-1 ${activeDrawer === item.key ? "text-white/70" : "text-ink-400"}`}>{item.hint}</div>
                </button>
              ))}
            </div>
          </div>
        </aside>

        <div className="space-y-5">
          {error && (
            <div className="flex items-start gap-3 rounded-2xl bg-red-50 border border-red-100 p-4">
              <div className="flex-shrink-0 w-1 h-full min-h-[1.5rem] rounded-full bg-red-400" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          )}

          <section ref={queryRef} className="archive-surface overflow-hidden">
            <button onClick={() => toggleDrawer("query")} className="w-full text-left px-6 py-5 flex items-center justify-between gap-4 hover:bg-canvas-100/50 transition-colors">
              <div>
                <div className="section-title mb-2">Drawer 01</div>
                <h2 className="text-xl font-semibold text-ink-900">检索问答抽屉</h2>
                <p className="mt-1 text-sm text-ink-500 leading-6">以当前问题为中心，查看答案、置信度与引用来源。</p>
              </div>
              <span className={`text-ink-400 transition-transform ${openDrawers.query ? "rotate-90" : ""}`}>▶</span>
            </button>
            {openDrawers.query && (
              <div className="border-t border-black/5 p-6 bg-white/70">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-10 h-10 rounded-lg bg-primary-50 flex items-center justify-center">
                    <svg className="w-5 h-5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-ink-900">智能问答</h3>
                    <p className="text-sm text-ink-400">基于文档和知识库的精准检索</p>
                  </div>
                </div>

                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={4}
                  className="morandi-input min-h-[120px] resize-none"
                  placeholder="输入您的问题..."
                />

                <div className="flex flex-col gap-4 mt-4 sm:flex-row sm:items-center sm:justify-between">
                  <label className="flex items-center gap-3 cursor-pointer group">
                    <div className="relative">
                      <input type="checkbox" checked={useWiki} onChange={(e) => setUseWiki(e.target.checked)} className="peer sr-only" />
                      <div className="w-5 h-5 rounded border-2 border-black/10 bg-white transition-all duration-200 peer-checked:border-primary-500 peer-checked:bg-primary-500 peer-focus:ring-2 peer-focus:ring-primary-100 flex items-center justify-center">
                        {useWiki && (
                          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                          </svg>
                        )}
                      </div>
                    </div>
                    <span className="text-sm text-ink-600 group-hover:text-ink-800 transition-colors">同时查询 Wiki 知识库</span>
                  </label>

                  <button onClick={handleQuery} disabled={loading || !query.trim()} className="btn-primary rounded-full px-6 py-3 text-sm disabled:opacity-50 disabled:cursor-not-allowed">
                    {loading ? "查询中..." : "开始查询"}
                  </button>
                </div>

                {response && (
                  <div className="mt-6 archive-card p-5">
                    <div className="flex justify-between items-start gap-4 mb-5">
                      <div>
                        <div className="section-title mb-2">Response</div>
                        <h3 className="text-lg font-semibold text-ink-900">回答结果</h3>
                      </div>
                      <div className="flex items-center gap-2 flex-wrap justify-end">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getConfidenceColor(response.confidence)}`}>
                          置信度 {(response.confidence * 100).toFixed(0)}%
                        </span>
                        <span className="drawer-handle bg-white border border-black/5 text-ink-500">{response.response_time.toFixed(2)}s</span>
                      </div>
                    </div>

                    <div className="border-l-4 border-primary-200 pl-4 mb-6">
                      <p className="text-ink-700 leading-relaxed whitespace-pre-wrap">{response.answer}</p>
                    </div>

                    {response.sources.length > 0 && (
                      <div>
                        <div className="section-title mb-2">Sources</div>
                        <div className="space-y-3">
                          {response.sources.map((source, idx) => (
                            <div key={idx} className="rounded-2xl border border-black/5 p-4 bg-white/90">
                              <div className="flex justify-between items-start gap-4">
                                <div className="flex items-center gap-2">
                                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 text-ink-800 flex items-center justify-center text-xs font-bold">{idx + 1}</span>
                                  <span className="text-sm font-medium text-ink-800">{source.doc_id || source.source || source.title || "来源"}</span>
                                </div>
                                {source.score !== undefined && (
                                  <span className="drawer-handle bg-white border border-black/5 text-ink-500">相关度 {(source.score * 100).toFixed(0)}%</span>
                                )}
                              </div>
                              <p className="text-sm text-ink-500 mt-3 leading-relaxed pl-8">
                                {source.excerpt || source.content || source.text || JSON.stringify(source).substring(0, 200)}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </section>

          <section ref={uploadRef} className="archive-surface overflow-hidden">
            <button onClick={() => toggleDrawer("upload")} className="w-full text-left px-6 py-5 flex items-center justify-between gap-4 hover:bg-canvas-100/50 transition-colors">
              <div>
                <div className="section-title mb-2">Drawer 02</div>
                <h2 className="text-xl font-semibold text-ink-900">文档入库抽屉</h2>
                <p className="mt-1 text-sm text-ink-500 leading-6">把 PDF、Word、Markdown 等文档上传进资源工作区。</p>
              </div>
              <span className={`text-ink-400 transition-transform ${openDrawers.upload ? "rotate-90" : ""}`}>▶</span>
            </button>
            {openDrawers.upload && (
              <div className="border-t border-black/5 p-6 bg-white/70">
                <div className="border-2 border-dashed border-black/10 rounded-2xl p-4 text-center hover:border-primary-300 transition-colors duration-200 mb-4">
                  <input
                    type="file"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    accept=".pdf,.docx,.doc,.md,.txt"
                    className="w-full text-sm text-ink-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-medium file:bg-primary-100 file:text-ink-800 hover:file:bg-primary-200 file:transition-colors file:cursor-pointer"
                  />
                  <p className="text-xs text-ink-400 mt-2">PDF、Word、Markdown、TXT</p>
                </div>
                <button onClick={handleUpload} disabled={!uploadFile} className="btn-primary w-full rounded-full py-3 text-sm disabled:opacity-50 disabled:cursor-not-allowed">
                  上传文档
                </button>
                {uploadStatus && (
                  <p className={`mt-3 text-sm text-center ${uploadStatus.includes("成功") ? "text-emerald-600" : uploadStatus.includes("失败") ? "text-red-600" : "text-ink-500"}`}>
                    {uploadStatus}
                  </p>
                )}
              </div>
            )}
          </section>

          <section ref={guideRef} className="archive-surface overflow-hidden">
            <button onClick={() => toggleDrawer("guide")} className="w-full text-left px-6 py-5 flex items-center justify-between gap-4 hover:bg-canvas-100/50 transition-colors">
              <div>
                <div className="section-title mb-2">Drawer 03</div>
                <h2 className="text-xl font-semibold text-ink-900">使用说明抽屉</h2>
                <p className="mt-1 text-sm text-ink-500 leading-6">查看资源库的工作方式：问答、混合检索与 Wiki 协同。</p>
              </div>
              <span className={`text-ink-400 transition-transform ${openDrawers.guide ? "rotate-90" : ""}`}>▶</span>
            </button>
            {openDrawers.guide && (
              <div className="border-t border-black/5 p-6 bg-white/70">
                <div className="space-y-4">
                  {[
                    { title: "智能问答", desc: "基于上传的文档和 Wiki 知识库回答问题" },
                    { title: "混合检索", desc: "结合向量检索和关键词检索，提高召回准确性" },
                    { title: "Wiki 查询", desc: "优先查询结构化的语言学理论知识" },
                  ].map((item, idx) => (
                    <div key={idx} className="archive-card p-4">
                      <div className="text-sm font-semibold text-ink-900">{item.title}</div>
                      <p className="text-sm text-ink-500 mt-2 leading-6">{item.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          <section ref={samplesRef} className="archive-surface overflow-hidden">
            <button onClick={() => toggleDrawer("samples")} className="w-full text-left px-6 py-5 flex items-center justify-between gap-4 hover:bg-canvas-100/50 transition-colors">
              <div>
                <div className="section-title mb-2">Drawer 04</div>
                <h2 className="text-xl font-semibold text-ink-900">热门问题抽屉</h2>
                <p className="mt-1 text-sm text-ink-500 leading-6">快速把常见问题塞入检索问答抽屉，减少第一次上手成本。</p>
              </div>
              <span className={`text-ink-400 transition-transform ${openDrawers.samples ? "rotate-90" : ""}`}>▶</span>
            </button>
            {openDrawers.samples && (
              <div className="border-t border-black/5 p-6 bg-white/70">
                <div className="flex flex-wrap gap-2">
                  {sampleQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setQuery(q);
                        setActiveDrawer("query");
                        queryRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
                      }}
                      className="text-sm text-ink-600 bg-white hover:bg-primary-50 hover:text-ink-900 px-3 py-2 rounded-xl border border-black/5 hover:border-primary-200 transition-all duration-200 text-left leading-snug"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
