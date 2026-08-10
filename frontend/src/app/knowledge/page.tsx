"use client";

import React, { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api";

interface Theory {
  name: string;
  title: string;
  domain: string;
  tags: string[];
}

interface SearchResult {
  page_name: string;
  title: string;
  summary: string;
  relevance_score: number;
  match_type: string;
  matched_sections: string[];
  tags: string[];
}

export default function KnowledgePage() {
  const [theories, setTheories] = useState<Theory[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [selectedTheory, setSelectedTheory] = useState<string | null>(null);
  const [theoryResults, setTheoryResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeDrawer, setActiveDrawer] = useState<string | null>(null);
  const [openDrawers, setOpenDrawers] = useState<Record<string, boolean>>({});

  useEffect(() => {
    void loadTheories();
  }, []);

  const groupedTheories = useMemo(() => {
    const groups = theories.reduce<Record<string, Theory[]>>((acc, theory) => {
      const key = (theory.title[0] || "#").toUpperCase();
      acc[key] = acc[key] || [];
      acc[key].push(theory);
      return acc;
    }, {});

    return Object.entries(groups)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([letter, items]) => ({
        letter,
        items: items.sort((a, b) => a.title.localeCompare(b.title)),
      }));
  }, [theories]);

  const loadTheories = async () => {
    try {
      const tags: string[] = await apiGet("/wiki/tags");
      const META_PREFIXES = ["concept-layer:", "type:", "theory-layer:", "source:", "function:"];
      const filtered = tags.filter((tag) => !META_PREFIXES.some((p) => tag.startsWith(p)));
      const theoryList: Theory[] = filtered.map((tag) => ({
        name: tag,
        title: tag.replace(/-/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
        domain: "理论",
        tags: [tag],
      }));
      setTheories(theoryList);

      const initialGroups = theoryList.reduce<Record<string, boolean>>((acc, theory) => {
        const key = (theory.title[0] || "#").toUpperCase();
        if (!(key in acc)) acc[key] = Object.keys(acc).length < 3;
        return acc;
      }, {});
      setOpenDrawers(initialGroups);
      const firstLetter = Object.keys(initialGroups)[0] || null;
      setActiveDrawer(firstLetter);
    } catch {
      // ignore
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await apiGet(`/wiki/search?query=${encodeURIComponent(searchQuery)}&max_results=10`);
      setSearchResults(Array.isArray(data) ? data : []);
      setSelectedTheory(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "搜索失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTheory = async (name: string, drawerKey?: string) => {
    setSelectedTheory(name);
    setLoading(true);
    setError(null);
    if (drawerKey) {
      setActiveDrawer(drawerKey);
      setOpenDrawers((prev) => ({ ...prev, [drawerKey]: true }));
    }
    try {
      const data = await apiGet(`/wiki/theory/${name}`);
      setTheoryResults(Array.isArray(data) ? data : []);
      setSearchResults([]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "获取理论内容失败");
    } finally {
      setLoading(false);
    }
  };

  const toggleDrawer = (letter: string) => {
    setOpenDrawers((prev) => ({ ...prev, [letter]: !prev[letter] }));
    setActiveDrawer(letter);
  };

  const getScoreBadgeColor = (score: number) => {
    if (score >= 0.7) return "bg-sage-100 text-ink-800 border border-sage-200";
    if (score >= 0.4) return "bg-accent-100 text-ink-900 border border-accent-200";
    return "bg-canvas-200 text-ink-700 border border-black/5";
  };

  const selectedTheoryTitle = selectedTheory?.replace(/-/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="max-w-7xl mx-auto brand-surface px-6 py-7 sm:px-8 sm:py-8 mb-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="section-title mb-2">Theory Archive</div>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-ink-900">知识库</h1>
            <p className="text-sm sm:text-base text-ink-500 mt-3 max-w-2xl leading-7">
              以理论档案馆的方式组织语言学知识，让理论名称、摘要与条目秩序保持清晰、可信、可检索。
            </p>
          </div>
          <div className="rounded-full bg-canvas-200 px-4 py-2 text-xs font-medium text-ink-600 shadow-soft self-start lg:self-auto">
            Morandi Theory Drawers
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto space-y-6">
        <section className="archive-surface p-6 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <svg className="h-5 w-5 text-ink-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd" />
                </svg>
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="morandi-input pl-12"
                placeholder="搜索理论、概念或关键词..."
              />
            </div>
            <button onClick={handleSearch} disabled={loading} className="btn-primary rounded-full px-6 py-3 text-sm disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? "搜索中" : "搜索"}
            </button>
          </div>

          {error && (
            <div className="mt-4 animate-slide-down flex items-start gap-3 rounded-xl bg-red-50 border border-red-100 p-4">
              <div className="flex-shrink-0 w-1 h-full min-h-[1.5rem] rounded-full bg-red-400" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {searchResults.length > 0 && (
            <div className="mt-6 space-y-3">
              <div className="section-title mb-2">Search Results</div>
              {searchResults.map((result, idx) => (
                <div
                  key={idx}
                  className="group relative rounded-2xl border border-black/5 p-4 cursor-pointer transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 hover:border-primary-200 bg-white"
                  onClick={() => handleSelectTheory(result.page_name, (result.title[0] || "#").toUpperCase())}
                >
                  <div className="flex justify-between items-start gap-4">
                    <div className="min-w-0 flex-1">
                      <h4 className="font-semibold text-ink-900 group-hover:text-primary-700 transition-colors">{result.title}</h4>
                      <p className="text-sm text-ink-500 mt-1.5 line-clamp-2 leading-relaxed">{result.summary?.substring(0, 200) ?? ""}...</p>
                    </div>
                    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${getScoreBadgeColor(result.relevance_score)}`}>
                      {(result.relevance_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-[320px_minmax(0,1fr)] gap-8">
          <aside className="archive-surface p-6 lg:sticky lg:top-8 self-start">
            <div className="mb-5">
              <div className="section-title mb-2">Drawer Index</div>
              <h2 className="text-xl font-semibold text-ink-900">理论抽屉</h2>
              <p className="mt-2 text-sm text-ink-500 leading-6">按首字母分组展开理论档案，保持当前抽屉与当前条目始终可见。</p>
            </div>

            {groupedTheories.length === 0 ? (
              <div className="text-center py-10">
                <div className="mx-auto w-12 h-12 rounded-full bg-gray-50 flex items-center justify-center mb-3">
                  <svg className="w-6 h-6 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                  </svg>
                </div>
                <p className="text-sm text-gray-400">暂无理论数据</p>
              </div>
            ) : (
              <div className="space-y-3">
                {groupedTheories.map(({ letter, items }) => (
                  <div key={letter} className="rounded-2xl border border-black/5 overflow-hidden bg-white/80">
                    <button onClick={() => toggleDrawer(letter)} className={`w-full text-left px-4 py-3 flex items-center justify-between transition-colors ${activeDrawer === letter ? "bg-canvas-100" : "hover:bg-canvas-100/60"}`}>
                      <div>
                        <div className="text-sm font-semibold text-ink-900">{letter} 抽屉</div>
                        <div className="text-xs text-ink-400 mt-1">{items.length} 个理论条目</div>
                      </div>
                      <span className={`text-ink-400 transition-transform ${openDrawers[letter] ? "rotate-90" : ""}`}>▶</span>
                    </button>
                    {openDrawers[letter] && (
                      <div className="border-t border-black/5 px-2 py-2">
                        {items.map((theory) => (
                          <button
                            key={theory.name}
                            onClick={() => handleSelectTheory(theory.name, letter)}
                            className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition-colors ${
                              selectedTheory === theory.name
                                ? "bg-archive-800 text-white"
                                : "text-ink-600 hover:bg-canvas-100 hover:text-ink-900"
                            }`}
                          >
                            {theory.title}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </aside>

          <section className="archive-surface p-6 min-h-[420px]">
            {selectedTheory ? (
              <div>
                <div className="flex flex-wrap items-center gap-2 mb-4">
                  {activeDrawer && <span className="drawer-handle">{activeDrawer} 抽屉</span>}
                  <span className="drawer-handle bg-white border border-black/5 text-ink-500">当前理论</span>
                </div>
                <h2 className="text-2xl font-semibold text-ink-900 mb-6">{selectedTheoryTitle}</h2>
                {loading ? (
                  <div className="flex flex-col items-center justify-center py-16">
                    <div className="relative">
                      <div className="animate-spin rounded-full h-10 w-10 border-2 border-primary-200" />
                      <div className="absolute inset-0 animate-spin rounded-full h-10 w-10 border-2 border-transparent border-t-primary-600" />
                    </div>
                    <p className="mt-4 text-sm text-ink-400 animate-pulse">加载中...</p>
                  </div>
                ) : theoryResults.length > 0 ? (
                  <div className="space-y-4">
                    {theoryResults.map((result, idx) => (
                      <div key={idx} className="archive-card p-5">
                        <h3 className="text-base font-semibold text-ink-900">{result.title}</h3>
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {result.tags.map((tag, i) => (
                            <span key={i} className="inline-flex items-center rounded-full bg-primary-100 px-2.5 py-0.5 text-xs font-medium text-ink-800 border border-primary-200">
                              {tag}
                            </span>
                          ))}
                        </div>
                        <p className="text-sm text-ink-600 mt-3 whitespace-pre-wrap leading-relaxed">{result.summary}</p>
                        {result.matched_sections.length > 0 && (
                          <div className="mt-4 flex flex-wrap items-center gap-2">
                            <span className="text-xs font-medium text-ink-400">匹配章节:</span>
                            {result.matched_sections.map((s, i) => (
                              <span key={i} className="inline-flex items-center rounded-md bg-canvas-100 px-2 py-1 text-xs text-ink-500 border border-black/5">
                                {s}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-16">
                    <div className="w-16 h-16 rounded-full bg-gray-50 flex items-center justify-center mb-4">
                      <svg className="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
                      </svg>
                    </div>
                    <p className="text-sm text-gray-400">未找到相关理论内容</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="w-16 h-16 rounded-full bg-primary-50 flex items-center justify-center mb-4">
                  <svg className="w-8 h-8 text-primary-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-ink-500">选择左侧的理论抽屉查看详细内容</p>
                <p className="text-xs text-ink-400 mt-1">点击理论名称开始探索</p>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
