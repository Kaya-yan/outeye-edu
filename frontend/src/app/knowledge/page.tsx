"use client";

import React, { useState, useEffect } from "react";

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
      const tagsRes = await fetch("/api/v1/wiki/tags");
      if (tagsRes.ok) {
        const tags: string[] = await tagsRes.json();
        const theoryList: Theory[] = tags.map((tag) => ({
          name: tag,
          title: tag.replace(/-/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
          domain: "理论",
          tags: [tag],
        }));
        setTheories(theoryList);
      }
    } catch {
      // 静默失败
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/v1/wiki/search?query=${encodeURIComponent(searchQuery)}&max_results=10`
      );
      if (response.ok) {
        const data = await response.json();
        setSearchResults(Array.isArray(data) ? data : []);
      } else {
        const errData = await response.json().catch(() => ({}));
        setError(errData.detail || `搜索失败 (${response.status})`);
      }
    } catch {
      setError("网络错误，请检查后端服务是否运行");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTheory = async (name: string) => {
    setSelectedTheory(name);
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/wiki/theory/${name}`);
      if (response.ok) {
        const data = await response.json();
        setTheoryResults(Array.isArray(data) ? data : []);
      } else {
        const errData = await response.json().catch(() => ({}));
        setError(errData.detail || `获取理论内容失败 (${response.status})`);
      }
    } catch {
      setError("网络错误，请检查后端服务是否运行");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">知识库</h1>
          <p className="text-gray-600 mt-1">
            基于LLM Wiki的12大语言学理论知识体系
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* 搜索区域 */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <div className="flex space-x-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="搜索理论、概念或关键词..."
            />
            <button
              onClick={handleSearch}
              disabled={loading}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "搜索中..." : "搜索"}
            </button>
          </div>

          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
              {error}
            </div>
          )}

          {/* 搜索结果 */}
          {searchResults.length > 0 && (
            <div className="mt-4 space-y-3">
              <h3 className="font-semibold text-gray-900">搜索结果</h3>
              {searchResults.map((result, idx) => (
                <div
                  key={idx}
                  className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() => handleSelectTheory(result.page_name)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-blue-600">
                        {result.title}
                      </h4>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                        {result.summary?.substring(0, 200) ?? ""}...
                      </p>
                    </div>
                    <span className="text-sm text-gray-500">
                      相关度: {(result.relevance_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 理论列表 */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold mb-4">语言学理论</h2>

            {theories.length === 0 ? (
              <p className="text-sm text-gray-500">暂无理论数据，请确保Wiki知识库已加载</p>
            ) : (
              <div className="space-y-2">
                {theories.map((theory) => (
                  <button
                    key={theory.name}
                    onClick={() => handleSelectTheory(theory.name)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm ${
                      selectedTheory === theory.name
                        ? "bg-blue-100 text-blue-700"
                        : "hover:bg-gray-100"
                    }`}
                  >
                    {theory.title}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 理论内容 */}
          <div className="lg:col-span-2 bg-white rounded-lg shadow-md p-6">
            {selectedTheory ? (
              <div>
                <h2 className="text-lg font-semibold mb-4">
                  {selectedTheory.replace(/-/g, " ").replace(/\b\w/g, (l) =>
                    l.toUpperCase()
                  )}
                </h2>
                {loading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-gray-500">加载中...</p>
                  </div>
                ) : theoryResults.length > 0 ? (
                  <div className="space-y-4">
                    {theoryResults.map((result, idx) => (
                      <div key={idx} className="border rounded-lg p-4">
                        <h3 className="font-semibold text-gray-900">{result.title}</h3>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {result.tags.map((tag, i) => (
                            <span key={i} className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs">
                              {tag}
                            </span>
                          ))}
                        </div>
                        <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap">
                          {result.summary}
                        </p>
                        {result.matched_sections.length > 0 && (
                          <div className="mt-2">
                            <span className="text-xs text-gray-500">匹配章节: </span>
                            {result.matched_sections.map((s, i) => (
                              <span key={i} className="text-xs text-gray-500">{s} </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    <p>未找到相关理论内容</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-12">
                <p>选择左侧的理论查看详细内容</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
