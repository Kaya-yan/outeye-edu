"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
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
  source_text?: string;
  furthest_step?: string | null;
}

const RESUME_KEY = "outeye:resume-project";

function progressOf(p: Project): { label: string; className: string; dot: string } {
  switch (p.furthest_step) {
    case "confirmed":
      return { label: "教案已确认", className: "bg-accent-100 text-ink-900 border border-accent-200", dot: "bg-accent-500" };
    case "plan":
      return { label: "教案已生成", className: "bg-sage-100 text-ink-800 border border-sage-200", dot: "bg-sage-500" };
    default:
      break;
  }
  switch (p.analysis_status) {
    case "processing":
      return { label: "分析中", className: "bg-accent-100 text-ink-900 border border-accent-200", dot: "bg-accent-500" };
    case "pending":
      return { label: "待分析", className: "bg-canvas-200 text-ink-700 border border-black/5", dot: "bg-ink-300" };
    case "completed":
      return { label: "分析完成", className: "bg-sage-100 text-ink-800 border border-sage-200", dot: "bg-sage-500" };
    default:
      return { label: p.analysis_status, className: "bg-canvas-200 text-ink-700 border border-black/5", dot: "bg-ink-300" };
  }
}

export default function HistoryPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const data = await apiGet<Project[]>("/projects/");
        setProjects([...data].sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at)));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "加载历史记录失败");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return projects;
    return projects.filter((p) => p.title.toLowerCase().includes(q));
  }, [projects, query]);

  const resume = (p: Project) => {
    try {
      sessionStorage.setItem(
        RESUME_KEY,
        JSON.stringify({
          id: p.id,
          title: p.title,
          source_text: p.source_text || "",
          student_level: p.student_level,
          course_type: p.course_type,
          duration_minutes: p.duration_minutes,
          auto_analyze: p.analysis_status === "completed",
        })
      );
    } catch {
      // 存不进去也照样回工作台
    }
    router.push("/");
  };

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="mx-auto mb-6 max-w-4xl">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900 sm:text-3xl">历史记录</h1>
        <p className="mt-2 text-sm text-ink-500">每条备课记录都保存在这里，点击可继续。</p>
        <div className="mt-5">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="按课文标题搜索…"
            className="morandi-input"
          />
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-3">
        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 p-4">
            <div className="min-h-[1.5rem] w-1 flex-shrink-0 rounded-full bg-red-400" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {loading ? (
          [...Array(4)].map((_, i) => <div key={i} className="archive-surface h-20 animate-pulse" />)
        ) : filtered.length === 0 ? (
          <div className="archive-surface px-6 py-16 text-center">
            <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-3xl bg-canvas-200 shadow-soft">
              <svg className="h-10 w-10 text-ink-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
              </svg>
            </div>
            {projects.length === 0 ? (
              <>
                <h2 className="text-lg font-semibold text-ink-900">还没有记录</h2>
                <p className="mt-2 text-sm text-ink-500">去工作台开始第一课吧。</p>
                <Link href="/" className="btn-primary mt-6">
                  去工作台
                </Link>
              </>
            ) : (
              <p className="text-sm text-ink-500">没有匹配“{query.trim()}”的记录。</p>
            )}
          </div>
        ) : (
          filtered.map((p) => {
            const progress = progressOf(p);
            return (
              <button
                key={p.id}
                onClick={() => resume(p)}
                className="archive-card flex w-full items-center gap-4 px-5 py-4 text-left"
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate text-base font-medium text-ink-900">{p.title || "未命名课文"}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-400">
                    {p.course_type && <span>{p.course_type}</span>}
                    {p.course_type && <span aria-hidden>·</span>}
                    <span>{new Date(p.created_at).toLocaleDateString("zh-CN")}</span>
                  </div>
                </div>
                <span className={`inline-flex flex-shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${progress.className}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${progress.dot}`} />
                  {progress.label}
                </span>
                <svg className="h-4 w-4 flex-shrink-0 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            );
          })
        )}
      </main>
    </div>
  );
}
