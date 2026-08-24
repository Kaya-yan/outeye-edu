"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api";

interface ComponentDef {
  id: string;
  scope: string;
  name: string;
  slug: string;
  summary: string | null;
  preview_cover: string | null;
  category: string | null;
  teaching_stage: string | null;
  subject_tags: string[];
  interaction_level: string | null;
  mode_support: string;
  community_status: string;
  owner_user_id: string | null;
  updated_at: string;
}

const SCOPE_TABS = [
  { key: "official", label: "官方组件" },
  { key: "personal", label: "我的组件" },
  { key: "community", label: "社区共享" },
] as const;

const CATEGORIES = ["课程导入", "知识讲授", "阅读分析", "活动组织", "检测反馈", "总结反思", "作业延伸", "教师辅助"];

const getCategoryLabel = (cat: string) => {
  const map: Record<string, string> = {
    "课程导入": "导入", "知识讲授": "讲授", "阅读分析": "阅读",
    "活动组织": "活动", "检测反馈": "检测", "总结反思": "总结",
    "作业延伸": "作业", "教师辅助": "辅助",
  };
  return map[cat] || cat;
};

const getCategoryColor = (cat: string) => {
  const colors: Record<string, string> = {
    "课程导入": "bg-amber-50 text-amber-700", "知识讲授": "bg-blue-50 text-blue-700",
    "阅读分析": "bg-emerald-50 text-emerald-700", "活动组织": "bg-violet-50 text-violet-700",
    "检测反馈": "bg-rose-50 text-rose-700", "总结反思": "bg-cyan-50 text-cyan-700",
    "作业延伸": "bg-orange-50 text-orange-700", "教师辅助": "bg-gray-50 text-gray-700",
  };
  return colors[cat] || "bg-gray-50 text-gray-700";
};

export default function ComponentLibraryPage() {
  const [scope, setScope] = useState<string>("official");
  const [category, setCategory] = useState<string | null>(null);
  const [components, setComponents] = useState<ComponentDef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [submitMsg, setSubmitMsg] = useState<string | null>(null);

  const loadComponents = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (scope) params.set("scope", scope);
      if (category) params.set("category", category);
      const data = await apiGet<ComponentDef[]>(`/courseware/components?${params.toString()}`);
      setComponents(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "加载组件列表失败");
    } finally {
      setLoading(false);
    }
  }, [scope, category]);

  useEffect(() => {
    loadComponents();
  }, [loadComponents]);

  const handleDownload = async (comp: ComponentDef) => {
    if (comp.scope !== "community") return;
    setDownloading(comp.id);
    try {
      await apiPost("/courseware/components", {
        name: comp.name,
        slug: `${comp.slug}-copy-${Date.now()}`,
        summary: comp.summary,
        preview_cover: comp.preview_cover,
        category: comp.category,
        teaching_stage: comp.teaching_stage,
        subject_tags: comp.subject_tags,
        interaction_level: comp.interaction_level,
        mode_support: comp.mode_support,
        scope: "personal",
        is_publishable: false,
        community_status: "draft",
      });
      setDownloading(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "下载失败");
      setDownloading(null);
    }
  };

  const handleSubmitToCommunity = async (comp: ComponentDef) => {
    if (comp.community_status === "submitted") return;
    setSubmitting(comp.id);
    try {
      await apiPost("/courseware/components/" + comp.id + "/submit");
      setSubmitMsg("已提交到社区");
      setTimeout(function () { setSubmitMsg(null); }, 2000);
      loadComponents();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setSubmitting(null);
    }
  };

  const getScopeLabel = (s: string) => {
    if (s === "official") return "官方";
    if (s === "personal") return "个人";
    return "社区";
  };

  const getScopeBadge = (s: string) => {
    if (s === "official") return "bg-primary-50 text-primary-700 ring-primary-700/10";
    if (s === "personal") return "bg-gray-50 text-gray-600 ring-gray-500/10";
    return "bg-violet-50 text-violet-700 ring-violet-700/10";
  };

  return (
    <div className="min-h-screen bg-gray-50/50">
      <header className="relative overflow-hidden bg-gradient-to-r from-amber-50 via-white to-white border-b border-gray-100">
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Link href="/history" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
            &larr; 返回历史记录
          </Link>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mt-2">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-amber-700 via-amber-600 to-amber-500 bg-clip-text text-transparent">
                教学组件库
              </h1>
              <p className="text-gray-500 mt-2 text-base">搭建课堂课件的高质量教学组件，像积木一样组装你的 HTML 课件</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-100 p-4 mb-6">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}
        {submitMsg && (
          <div className="flex items-start gap-3 rounded-xl bg-emerald-50 border border-emerald-100 p-4 mb-6">
            <p className="text-sm text-emerald-700">{submitMsg}</p>
          </div>
        )}

        {/* Scope tabs */}
        <div className="flex gap-2 mb-4">
          {SCOPE_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setScope(tab.key)}
              className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
                scope === tab.key
                  ? "bg-amber-600 text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-amber-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Category filter */}
        <div className="flex flex-wrap gap-1.5 mb-6">
          <button
            onClick={() => setCategory(null)}
            className={`px-3 py-1 text-xs rounded-full transition-colors ${
              !category ? "bg-gray-800 text-white" : "bg-white text-gray-600 border border-gray-200 hover:border-gray-400"
            }`}
          >
            全部
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                category === cat ? "bg-amber-600 text-white" : "bg-white text-gray-600 border border-gray-200 hover:border-amber-300"
              }`}
            >
              {getCategoryLabel(cat)}
            </button>
          ))}
        </div>

        {/* Component grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 p-4 animate-pulse">
                <div className="h-32 bg-gray-100 rounded-lg mb-3" />
                <div className="h-4 bg-gray-100 rounded w-3/4 mb-2" />
                <div className="h-3 bg-gray-100 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : components.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm ring-1 ring-gray-900/5 p-12 text-center">
            <div className="mx-auto w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">暂无组件</h3>
            <p className="text-sm text-gray-500">
              {scope === "official" ? "官方组件库即将上线" : scope === "personal" ? "你还没有创建个人组件" : "社区暂无共享组件"}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {components.map((comp) => (
              <div
                key={comp.id}
                className="group bg-white rounded-xl border border-gray-100 p-4 hover:shadow-md hover:border-amber-200 transition-all duration-200"
              >
                <div className="h-32 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg mb-3 flex items-center justify-center overflow-hidden">
                  {comp.preview_cover ? (
                    <img src={comp.preview_cover} alt={comp.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="text-center text-gray-300">
                      <svg className="w-10 h-10 mx-auto mb-1" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                        <rect x="3" y="3" width="18" height="18" rx="2" />
                        <path d="M9 9h6M9 13h6M9 17h3" />
                      </svg>
                      <span className="text-[10px]">暂无预览</span>
                    </div>
                  )}
                </div>
                <h3 className="text-sm font-semibold text-gray-900 mb-1 truncate">{comp.name}</h3>
                <p className="text-xs text-gray-500 line-clamp-2 mb-2 min-h-[2.5em]">
                  {comp.summary || "暂无简介"}
                </p>
                <div className="flex flex-wrap gap-1 mb-2">
                  {comp.category && (
                    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${getCategoryColor(comp.category)}`}>
                      {getCategoryLabel(comp.category)}
                    </span>
                  )}
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ring-1 ring-inset ${getScopeBadge(comp.scope)}`}>
                    {getScopeLabel(comp.scope)}
                  </span>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-gray-50">
                  <span className="text-[10px] text-gray-400">
                    {comp.mode_support === "both" ? "双模式" : comp.mode_support === "slides" ? "幻灯片" : "长页面"}
                  </span>
                  {comp.scope === "community" ? (
                    <button
                      onClick={() => handleDownload(comp)}
                      disabled={downloading === comp.id}
                      className="text-[10px] font-medium text-amber-600 hover:text-amber-700 disabled:opacity-50"
                    >
                      {downloading === comp.id ? "下载中…" : "下载"}
                    </button>
                  ) : comp.scope === "personal" && comp.community_status !== "submitted" ? (
                    <button
                      onClick={() => handleSubmitToCommunity(comp)}
                      disabled={submitting === comp.id}
                      className="text-[10px] font-medium text-violet-600 hover:text-violet-700 disabled:opacity-50"
                    >
                      {submitting === comp.id ? "提交中…" : "提交到社区"}
                    </button>
                  ) : comp.scope === "personal" && comp.community_status === "submitted" ? (
                    <span className="text-[10px] text-violet-400">审核中</span>
                  ) : (
                    <span className="text-[10px] text-gray-400">已拥有</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
