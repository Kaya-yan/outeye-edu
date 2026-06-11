"use client";

import React, { useState } from "react";

interface RAGResponse {
  answer: string;
  sources: Array<Record<string, any>>;
  confidence: number;
  response_time: number;
  model?: string;
}

export default function ResourcesPage() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [useWiki, setUseWiki] = useState(true);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const handleQuery = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const endpoint = useWiki
        ? "/api/v1/rag/query-with-wiki"
        : "/api/v1/rag/query";

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          method: "hybrid",
          top_k: 5,
          use_wiki: useWiki,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setResponse(data);
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.detail || `查询失败 (${res.status})`);
      }
    } catch {
      setError("网络错误，请检查后端服务是否运行");
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;

    setUploadStatus("上传中...");
    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      const res = await fetch("/api/v1/rag/upload-file", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setUploadStatus(`上传成功：${data.message}`);
      } else {
        setUploadStatus("上传失败");
      }
    } catch {
      setUploadStatus("上传失败");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">资源检索</h1>
          <p className="text-gray-600 mt-1">
            基于RAG的智能资源检索与问答
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 查询区域 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 查询输入 */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold mb-4">智能问答</h2>

              <div className="mb-4">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="输入您的问题..."
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={useWiki}
                    onChange={(e) => setUseWiki(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-600">
                    同时查询Wiki知识库
                  </span>
                </label>

                <button
                  onClick={handleQuery}
                  disabled={loading || !query.trim()}
                  className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? "查询中..." : "查询"}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
                {error}
              </div>
            )}

            {/* 回答结果 */}
            {response && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold">回答</h2>
                  <div className="flex items-center space-x-4 text-sm text-gray-500">
                    <span>置信度: {(response.confidence * 100).toFixed(0)}%</span>
                    <span>耗时: {response.response_time.toFixed(2)}秒</span>
                  </div>
                </div>

                <div className="prose prose-sm max-w-none mb-6">
                  <div className="whitespace-pre-wrap text-gray-700">
                    {response.answer}
                  </div>
                </div>

                {/* 来源 */}
                {response.sources.length > 0 && (
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-2">
                      参考来源
                    </h3>
                    <div className="space-y-3">
                      {response.sources.map((source, idx) => (
                        <div key={idx} className="border rounded-lg p-3 bg-gray-50">
                          <div className="flex justify-between items-start">
                            <span className="text-sm font-medium text-blue-600">
                              [{idx + 1}] {source.doc_id || source.source || source.title || '来源'}
                            </span>
                            {source.score !== undefined && (
                              <span className="text-xs text-gray-500">
                                相关度: {(source.score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mt-1">
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

          {/* 侧边栏 */}
          <div className="space-y-6">
            {/* 文档上传 */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold mb-4">文档上传</h2>

              <div className="mb-4">
                <input
                  type="file"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  accept=".pdf,.docx,.doc,.md,.txt"
                  className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>

              <button
                onClick={handleUpload}
                disabled={!uploadFile}
                className="w-full bg-green-600 text-white py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                上传文档
              </button>

              {uploadStatus && (
                <p className="mt-2 text-sm text-gray-600">{uploadStatus}</p>
              )}

              <p className="mt-4 text-xs text-gray-500">
                支持格式：PDF、Word、Markdown、TXT
              </p>
            </div>

            {/* 使用说明 */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold mb-4">使用说明</h2>

              <div className="space-y-3 text-sm text-gray-600">
                <p>
                  <strong>智能问答：</strong>基于上传的文档和Wiki知识库回答问题
                </p>
                <p>
                  <strong>混合检索：</strong>结合向量检索和关键词检索，提高准确性
                </p>
                <p>
                  <strong>Wiki查询：</strong>优先查询结构化的语言学理论知识
                </p>
              </div>
            </div>

            {/* 热门问题 */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold mb-4">热门问题</h2>

              <div className="space-y-2">
                {[
                  "Krashen i+1理论如何应用于课文选择？",
                  "如何评估课文的认知负荷？",
                  "Bloom分类学在教学设计中的应用？",
                  "什么是ZPD理论？",
                ].map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => setQuery(q)}
                    className="w-full text-left text-sm text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
