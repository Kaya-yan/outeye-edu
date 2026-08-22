"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/lib/api";

interface Project {
  id: string;
  title: string;
  course_type: string;
  student_level: string;
  duration_minutes: number;
  analysis_status: string;
  status: string;
  created_at: string;
}

type StatusKey = "all" | "completed" | "processing" | "pending";

const STATUS_ORDER: Exclude<StatusKey, "all">[] = ["processing", "pending", "completed"];

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<StatusKey>("all");
  const [openDrawers, setOpenDrawers] = useState<Record<Exclude<StatusKey, "all">, boolean>>({
    processing: true,
    pending: true,
    completed: true,
  });

  useEffect(() => {
    void loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await apiGet<Project[]>("/projects/");
      setProjects(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载项目列表失败");
    } finally {
      setLoading(false);
    }
  };

  const groupedProjects = useMemo(() => {
    return STATUS_ORDER.reduce<Record<Exclude<StatusKey, "all">, Project[]>>((acc, status) => {
      acc[status] = projects.filter((project) => project.analysis_status === status);
      return acc;
    }, { processing: [], pending: [], completed: [] });
  }, [projects]);

  const filteredStatuses: Exclude<StatusKey, "all">[] = activeFilter === "all" ? STATUS_ORDER : [activeFilter as Exclude<StatusKey, "all">];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-sage-100 text-ink-800 border border-sage-200";
      case "processing":
        return "bg-accent-100 text-ink-900 border border-accent-200";
      case "pending":
        return "bg-canvas-200 text-ink-700 border border-black/5";
      default:
        return "bg-canvas-200 text-ink-700 border border-black/5";
    }
  };

  const getStatusDotColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-sage-500";
      case "processing":
        return "bg-accent-500";
      case "pending":
        return "bg-ink-300";
      default:
        return "bg-ink-300";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "completed":
        return "已完成";
      case "processing":
        return "分析中";
      case "pending":
        return "待分析";
      default:
        return status;
    }
  };

  const getDrawerSummary = (status: Exclude<StatusKey, "all">) => {
    switch (status) {
      case "processing":
        return "正在分析中的任务。";
      case "pending":
        return "等待进入分析或等待后续教学设计的档案。";
      case "completed":
        return "已完成分析、可继续进入课件或复盘的历史项目。";
    }
  };

  const toggleDrawer = (status: Exclude<StatusKey, "all">) => {
    setOpenDrawers((prev) => ({ ...prev, [status]: !prev[status] }));
  };

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="max-w-7xl mx-auto brand-surface px-6 py-7 sm:px-8 sm:py-8 mb-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="section-title mb-2">Archive Project Center</div>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-ink-900">项目管理</h1>
            <p className="text-sm sm:text-base text-ink-500 mt-3 max-w-2xl leading-7">
              管理课文分析、教案与课件项目，可定位、筛选与继续。
            </p>
          </div>
          <Link href="/analysis" className="btn-archive self-start sm:self-auto">
            新建分析
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto space-y-6">
        {error && (
          <div className="animate-slide-down flex items-start gap-3 rounded-xl bg-red-50 border border-red-100 p-4">
            <div className="flex-shrink-0 w-1 h-full min-h-[1.5rem] rounded-full bg-red-400" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <section className="page-surface-strong px-6 py-6 sm:px-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="section-title mb-2">Archive Filters</div>
              <h2 className="text-2xl font-semibold text-ink-900">先筛选抽屉，再进入具体项目</h2>
              <p className="mt-3 text-sm text-ink-500 leading-7 max-w-2xl">
                抽屉、筛选状态与条目归属都清楚可见，便于定位每个项目。
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:w-[440px]">
              <Metric label="全部项目" value={projects.length} />
              <Metric label="分析中" value={groupedProjects.processing.length} />
              <Metric label="待分析" value={groupedProjects.pending.length} />
              <Metric label="已完成" value={groupedProjects.completed.length} />
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            {[
              { key: "all", label: "全部抽屉" },
              { key: "processing", label: "分析中" },
              { key: "pending", label: "待分析" },
              { key: "completed", label: "已完成" },
            ].map((item) => (
              <button
                key={item.key}
                onClick={() => setActiveFilter(item.key as StatusKey)}
                className={`rounded-full px-4 py-2 text-sm transition-colors ${
                  activeFilter === item.key
                    ? "bg-archive-800 text-white"
                    : "bg-white text-ink-600 border border-black/5 hover:bg-canvas-100"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </section>

        {loading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="archive-surface p-6 animate-pulse" style={{ animationDelay: `${i * 150}ms` }}>
                <div className="h-5 bg-gray-200 rounded-lg w-2/5 mb-4" />
                <div className="h-20 bg-gray-100 rounded-2xl" />
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="archive-surface p-12 text-center">
            <div className="mx-auto w-24 h-24 rounded-[28px] bg-canvas-200 flex items-center justify-center mb-6 shadow-soft">
              <svg className="w-12 h-12 text-archive-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
              </svg>
            </div>
            <div className="section-title mb-2">No archive yet</div>
            <h2 className="text-2xl font-semibold text-ink-900 mb-2">暂无项目</h2>
            <p className="text-ink-500 mb-8 max-w-sm mx-auto leading-7">
              从第一个课文分析开始，项目、方案与课件会自然积累在这里。
            </p>
            <Link href="/analysis" className="btn-archive">
              开始分析
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredStatuses.map((status) => {
              const drawerProjects = groupedProjects[status];
              const isOpen = openDrawers[status];
              return (
                <section key={status} className="archive-surface overflow-hidden">
                  <button
                    onClick={() => toggleDrawer(status)}
                    className="w-full text-left px-6 py-5 flex items-center justify-between gap-4 hover:bg-canvas-100/50 transition-colors"
                  >
                    <div>
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium ${getStatusColor(status)}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${getStatusDotColor(status)}`} />
                          {getStatusText(status)}
                        </span>
                        <span className="text-xs text-ink-400">{drawerProjects.length} 个项目</span>
                      </div>
                      <h3 className="mt-3 text-xl font-semibold text-ink-900">{getStatusText(status)} 抽屉</h3>
                      <p className="mt-1 text-sm text-ink-500 leading-6">{getDrawerSummary(status)}</p>
                    </div>
                    <span className={`text-ink-400 transition-transform ${isOpen ? "rotate-90" : ""}`}>▶</span>
                  </button>

                  {isOpen && (
                    <div className="border-t border-black/5 px-4 pb-4 pt-4 space-y-3 bg-white/60">
                      {drawerProjects.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-black/10 bg-canvas-100/60 px-5 py-6 text-sm text-ink-400">
                          当前抽屉暂无项目。
                        </div>
                      ) : (
                        drawerProjects.map((project, idx) => (
                          <div key={project.id} className="archive-card animate-slide-up" style={{ animationDelay: `${idx * 60}ms`, animationFillMode: "both" }}>
                            <div className="flex flex-col sm:flex-row sm:items-stretch">
                              <div className="sm:w-28 bg-archive-800 text-white px-5 py-4 sm:py-0 flex sm:flex-col sm:items-center sm:justify-center gap-1">
                                <div className="text-[11px] uppercase tracking-[0.18em] text-white/60">项目</div>
                                <div className="text-lg font-semibold leading-none">{project.student_level}</div>
                              </div>
                              <div className="px-5 py-4 sm:w-44 border-b sm:border-b-0 sm:border-r border-black/5 bg-canvas-100/70">
                                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">课程信息</div>
                                <div className="mt-3 text-sm font-medium text-ink-800">{project.course_type || "未分类课程"}</div>
                                <div className="mt-2 text-xs text-ink-400">{project.duration_minutes} 分钟</div>
                              </div>
                              <div className="flex-1 px-5 py-4 bg-white">
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                  <div className="min-w-0 flex-1">
                                    <h2 className="text-lg font-semibold text-ink-900 truncate">{project.title}</h2>
                                    <p className="mt-2 text-sm text-ink-500 leading-6">
                                      已收入你的工作台，可继续进入分析、课件或教学设计。
                                    </p>
                                  </div>
                                  <div className="flex items-center gap-2 self-start">
                                    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium ${getStatusColor(project.analysis_status)}`}>
                                      <span className={`h-1.5 w-1.5 rounded-full ${getStatusDotColor(project.analysis_status)}`} />
                                      {getStatusText(project.analysis_status)}
                                    </span>
                                  </div>
                                </div>
                                <div className="mt-4 flex flex-wrap items-center gap-2 pt-4 border-t border-black/5">
                                  <span className="drawer-handle">{project.course_type || "未分类课程"}</span>
                                  <span className="drawer-handle bg-white border border-black/5 text-ink-500">{project.student_level}</span>
                                  <span className="drawer-handle bg-white border border-black/5 text-ink-500">创建于 {new Date(project.created_at).toLocaleDateString("zh-CN")}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </section>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="data-card p-4 bg-white/90 text-center">
      <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-ink-900">{value}</div>
    </div>
  );
}
