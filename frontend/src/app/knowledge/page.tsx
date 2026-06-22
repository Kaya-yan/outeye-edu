"use client";

import React, { useState, useEffect } from "react";
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

  useEffect(() => {
    loadTheories();
  }, []);

  const loadTheories = async () => {
    try {
      const tags: string[] = await apiGet("/wiki/tags");
      // 过滤元数据标签（含冒号的前缀标签，如 concept-layer:, source: 等）
      const META_PREFIXES = ["concept-layer:", "type:", "theory-layer:", "source:", "function:"];
      const filtered = tags.filter(
        (tag) => !META_PREFIXES.some((p) => tag.startsWith(p))
      );
      const theoryList: Theory[] = filtered.map((tag) => ({
        name: tag,
        title: tag.replace(/-/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
        domain: "理论",
        tags: [tag],
      }));
      setTheories(theoryList);
    } catch {
      // 静默失败
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await apiGet(`/wiki/search?query=${encodeURIComponent(searchQuery)}&max_results=10`);
      setSearchResults(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "搜索失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTheory = async (name: string) => {
    setSelectedTheory(name);
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet(`/wiki/theory/${name}`);
      setTheoryResults(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "获取理论内容失败");
    } finally {
      setLoading(false);
    }
  };

  const getScoreBadgeColor = (score: number) => {
    if (score >= 0.7) return "bg-emerald-100 text-emerald-700 ring-emerald-600/20";
    if (score >= 0.4) return "bg-amber-100 text-amber-700 ring-amber-600/20";
    return "bg-gray-100 text-gray-600 ring-gray-500/20";
  };

  return (
    <div className="min-h-screen bg-gray-50/50">
      {/* Header */}
      <header className="relative overflow-hidden bg-gradient-to-r from-primary-50 via-white to-white border-b border-gray-100">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-primary-100/40 via-transparent to-transparent" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary-700 via-primary-600 to-primary-500 bg-clip-text text-transparent">
            知识库
          </h1>
          <p className="text-gray-500 mt-2 text-base">
            基于LLM Wiki的12大语言学理论知识体系
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Section */}
        <div className="bg-white rounded-2xl shadow-sm ring-1 ring-gray-900/5 p-6 mb-8 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <svg className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd" />
                </svg>
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="block w-full rounded-xl border-0 py-3.5 pl-12 pr-4 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-200 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-primary-500 sm:text-sm sm:leading-6 transition-shadow duration-200"
                placeholder="搜索理论、概念或关键词..."
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-primary-600 to-primary-500 px-6 py-3.5 text-sm font-semibold text-white shadow-sm hover:from-primary-700 hover:to-primary-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  搜索中
                </>
              ) : (
                "搜索"
              )}
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="mt-4 animate-slide-down flex items-start gap-3 rounded-xl bg-red-50 border border-red-100 p-4">
              <div className="flex-shrink-0 w-1 h-full min-h-[1.5rem] rounded-full bg-red-400" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="mt-6 space-y-3">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">搜索结果</h3>
              {searchResults.map((result, idx) => (
                <div
                  key={idx}
                  className="group relative rounded-xl border border-gray-100 p-4 cursor-pointer transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 hover:border-primary-200 bg-white"
                  onClick={() => handleSelectTheory(result.page_name)}
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <div className="flex justify-between items-start gap-4">
                    <div className="min-w-0 flex-1">
                      <h4 className="font-semibold text-primary-600 group-hover:text-primary-700 transition-colors">
                        {result.title}
                      </h4>
                      <p className="text-sm text-gray-500 mt-1.5 line-clamp-2 leading-relaxed">
                        {result.summary?.substring(0, 200) ?? ""}...
                      </p>
                    </div>
                    <span className={`flex-shrink-0 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${getScoreBadgeColor(result.relevance_score)}`}>
                      {(result.relevance_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Content Area - 2 Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Sidebar - Theory List */}
          <div className="lg:col-span-1">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm ring-1 ring-gray-900/5 p-6 sticky top-8">
              <div className="mb-5">
                <h2 className="text-lg font-bold text-gray-900">语言学理论</h2>
                <div className="mt-2 h-0.5 w-12 bg-gradient-to-r from-primary-500 to-primary-300 rounded-full" />
              </div>

              {theories.length === 0 ? (
                <div className="text-center py-10">
                  <div className="mx-auto w-12 h-12 rounded-full bg-gray-50 flex items-center justify-center mb-3">
                    <svg className="w-6 h-6 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                    </svg>
                  </div>
                  <p className="text-sm text-gray-400">暂无理论数据</p>
                  <p className="text-xs text-gray-300 mt-1">请确保Wiki知识库已加载</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {theories.map((theory) => (
                    <button
                      key={theory.name}
                      onClick={() => handleSelectTheory(theory.name)}
                      className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                        selectedTheory === theory.name
                          ? "bg-primary-50 text-primary-700 border-l-[3px] border-primary-500 pl-3"
                          : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                      }`}
                    >
                      {theory.title}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Content - Theory Details */}
          <div className="lg:col-span-2">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm ring-1 ring-gray-900/5 p-6 min-h-[400px]">
              {selectedTheory ? (
                <div>
                  <h2 className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent mb-6">
                    {selectedTheory.replace(/-/g, " ").replace(/\b\w/g, (l) =>
                      l.toUpperCase()
                    )}
                  </h2>
                  {loading ? (
                    <div className="flex flex-col items-center justify-center py-16">
                      <div className="relative">
                        <div className="animate-spin rounded-full h-10 w-10 border-2 border-primary-200" />
                        <div className="absolute inset-0 animate-spin rounded-full h-10 w-10 border-2 border-transparent border-t-primary-600" />
                      </div>
                      <p className="mt-4 text-sm text-gray-400 animate-pulse">加载中...</p>
                    </div>
                  ) : theoryResults.length > 0 ? (
                    <div className="space-y-4">
                      {theoryResults.map((result, idx) => (
                        <div
                          key={idx}
                          className="group rounded-xl border border-gray-100 p-5 transition-all duration-200 hover:shadow-md hover:border-gray-200"
                          style={{ animationDelay: `${idx * 80}ms` }}
                        >
                          <h3 className="text-base font-semibold text-gray-900 group-hover:text-primary-700 transition-colors">
                            {result.title}
                          </h3>
                          <div className="flex flex-wrap gap-1.5 mt-3">
                            {result.tags.map((tag, i) => (
                              <span
                                key={i}
                                className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                          <p className="text-sm text-gray-600 mt-3 whitespace-pre-wrap leading-relaxed">
                            {result.summary}
                          </p>
                          {result.matched_sections.length > 0 && (
                            <div className="mt-4 flex flex-wrap items-center gap-2">
                              <span className="text-xs font-medium text-gray-400">匹配章节:</span>
                              {result.matched_sections.map((s, i) => (
                                <span
                                  key={i}
                                  className="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs text-gray-500 ring-1 ring-inset ring-gray-200"
                                >
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
                  <p className="text-sm font-medium text-gray-500">选择左侧的理论查看详细内容</p>
                  <p className="text-xs text-gray-400 mt-1">点击理论名称开始探索</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
