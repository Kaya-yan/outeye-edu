"use client";

import React, { useState, useEffect } from "react";
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

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-emerald-50 text-emerald-700 ring-emerald-600/20";
      case "processing":
        return "bg-amber-50 text-amber-700 ring-amber-600/20";
      case "pending":
        return "bg-gray-50 text-gray-600 ring-gray-500/20";
      default:
        return "bg-gray-50 text-gray-600 ring-gray-500/20";
    }
  };

  const getStatusDotColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-emerald-500";
      case "processing":
        return "bg-amber-500";
      case "pending":
        return "bg-gray-400";
      default:
        return "bg-gray-400";
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

  return (
    <div className="min-h-screen bg-gray-50/50">
      {/* Header */}
      <header className="relative overflow-hidden bg-gradient-to-r from-primary-50 via-white to-white border-b border-gray-100">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-primary-100/40 via-transparent to-transparent" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-primary-700 via-primary-600 to-primary-500 bg-clip-text text-transparent">
                项目管理
              </h1>
              <p className="text-gray-500 mt-2 text-base">管理您的课文分析项目</p>
            </div>
            <Link
              href="/analysis"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-primary-600 to-primary-500 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:from-primary-700 hover:to-primary-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-all duration-200 self-start sm:self-auto"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              新建分析
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error */}
        {error && (
          <div className="animate-slide-down flex items-start gap-3 rounded-xl bg-red-50 border border-red-100 p-4 mb-6">
            <div className="flex-shrink-0 w-1 h-full min-h-[1.5rem] rounded-full bg-red-400" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Loading - Skeleton Loader */}
        {loading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="bg-white rounded-2xl shadow-sm ring-1 ring-gray-900/5 p-6 animate-pulse"
                style={{ animationDelay: `${i * 150}ms` }}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 space-y-3">
                    <div className="h-5 bg-gray-200 rounded-lg w-2/5" />
                    <div className="flex gap-3">
                      <div className="h-5 bg-gray-100 rounded-full w-20" />
                      <div className="h-5 bg-gray-100 rounded-full w-24" />
                      <div className="h-5 bg-gray-100 rounded-full w-16" />
                    </div>
                  </div>
                  <div className="h-6 bg-gray-100 rounded-full w-16" />
                </div>
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <div className="h-3 bg-gray-100 rounded w-32" />
                </div>
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          /* Empty State */
          <div className="bg-white rounded-2xl shadow-sm ring-1 ring-gray-900/5 p-12 text-center">
            <div className="mx-auto w-24 h-24 rounded-full bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center mb-6">
              <svg className="w-12 h-12 text-primary-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">暂无项目</h2>
            <p className="text-gray-500 mb-8 max-w-sm mx-auto">
              开始您的第一个课文分析项目，探索智能教研的无限可能
            </p>
            <Link
              href="/analysis"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-primary-600 to-primary-500 px-6 py-3.5 text-sm font-semibold text-white shadow-sm hover:from-primary-700 hover:to-primary-600 transition-all duration-200"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              开始分析
            </Link>
          </div>
        ) : (
          /* Project List */
          <div className="space-y-4">
            {projects.map((project, idx) => (
              <div
                key={project.id}
                className="group bg-white rounded-2xl shadow-sm ring-1 ring-gray-900/5 p-6 transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 hover:ring-gray-200 animate-slide-up"
                style={{ animationDelay: `${idx * 80}ms`, animationFillMode: "both" }}
              >
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <h2 className="text-lg font-semibold text-gray-900 group-hover:text-primary-700 transition-colors">
                      {project.title}
                    </h2>
                    <div className="flex flex-wrap items-center gap-2 mt-3">
                      <span className="inline-flex items-center rounded-full bg-primary-50 px-2.5 py-1 text-xs font-medium text-primary-700 ring-1 ring-inset ring-primary-700/10">
                        {project.course_type}
                      </span>
                      <span className="inline-flex items-center rounded-full bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
                        {project.student_level}
                      </span>
                      <span className="inline-flex items-center rounded-full bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
                        {project.duration_minutes}分钟
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 self-start">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium ring-1 ring-inset ${getStatusColor(
                        project.analysis_status
                      )}`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${getStatusDotColor(project.analysis_status)}`} />
                      {getStatusText(project.analysis_status)}
                    </span>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <p className="text-xs text-gray-400">
                    创建时间: {new Date(project.created_at).toLocaleString("zh-CN")}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
