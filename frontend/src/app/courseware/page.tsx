"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiGet, apiPost } from "@/lib/api";

interface CoursewareProject {
  id: string;
  title: string;
  mode: string;
  source_type: string;
  source_plan_id: string | null;
  status: string;
  updated_at: string;
  current_version_id: string | null;
}

const sourceLabels: Record<string, string> = {
  from_plan: "从教案生成",
  imported_html: "导入 HTML",
  blank_template: "空白模板",
};

const statusLabels: Record<string, string> = {
  ready_to_present: "可展示",
  in_editing: "编辑中",
  draft: "草稿",
  archived: "已归档",
};

export default function CoursewareListPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<CoursewareProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState<"slides" | "longform" | null>(null);

  useEffect(() => {
    void loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await apiGet<CoursewareProject[]>("/courseware");
      setProjects(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "加载课件列表失败");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBlank = async (mode: "slides" | "longform") => {
    setCreating(mode);
    setError(null);
    try {
      const result = await apiPost<{ project: CoursewareProject }>("/courseware", {
        title: `未命名课件 ${new Date().toLocaleDateString("zh-CN")}`,
        source_type: "blank_template",
        mode,
        template_id: "classroom_default",
      });
      router.push(`/courseware/${result.project.id}/edit`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "创建课件失败");
    } finally {
      setCreating(null);
    }
  };

  const summary = useMemo(() => {
    const slides = projects.filter((project) => project.mode === "slides").length;
    const longform = projects.length - slides;
    const fromPlan = projects.filter((project) => project.source_type === "from_plan").length;
    return {
      total: projects.length,
      slides,
      longform,
      fromPlan,
      latest: projects[0] || null,
    };
  }, [projects]);

  const getModeLabel = (mode: string) => (mode === "slides" ? "幻灯片" : "长页面");
  const getModeIcon = (mode: string) => (mode === "slides" ? "📊" : "📃");
  const getSourceLabel = (source: string) => sourceLabels[source] || source;
  const getStatusLabel = (status: string) => statusLabels[status] || status;

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="max-w-7xl mx-auto brand-surface px-6 py-7 sm:px-8 sm:py-8 mb-6 overflow-hidden relative">
        <div className="absolute right-[-6%] top-[-25%] h-56 w-56 rounded-full bg-primary-200/30 blur-3xl" />
        <div className="absolute left-[18%] bottom-[-30%] h-52 w-52 rounded-full bg-sage-200/25 blur-3xl" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="section-title mb-2">Courseware Workbench</div>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-ink-900">教学课件工作台</h1>
            <p className="text-sm sm:text-base text-ink-500 mt-3 leading-7">
              承接分析页的教案，生成可编辑、可展示的 HTML 课件。
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {['分析页生成', '课件项目管理', '编辑器继续工作', '课堂展示'].map((label) => (
                <span key={label} className="drawer-handle bg-white/85 border border-black/5 text-ink-600">
                  {label}
                </span>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/analysis" className="btn-secondary rounded-full px-5 py-3 text-sm">
              从分析页进入
            </Link>
            <Link href="/courseware/components" className="btn-secondary rounded-full px-5 py-3 text-sm">
              组件库
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto space-y-6">
        {error && (
          <div className="animate-slide-down flex items-start gap-3 rounded-2xl bg-red-50 border border-red-100 p-4">
            <div className="flex-shrink-0 w-1 h-full min-h-[1.5rem] rounded-full bg-red-400" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <section className="page-surface-strong px-6 py-6 sm:px-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="section-title mb-2">Primary Flow</div>
              <h2 className="text-2xl font-semibold text-ink-900">先从教案生成，再进入课件编辑与课堂展示</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:w-[420px]">
              <div className="data-card p-4 text-center bg-white/90">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Projects</div>
                <div className="mt-2 text-2xl font-semibold text-ink-900">{summary.total}</div>
              </div>
              <div className="data-card p-4 text-center bg-white/90">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Slides</div>
                <div className="mt-2 text-2xl font-semibold text-ink-900">{summary.slides}</div>
              </div>
              <div className="data-card p-4 text-center bg-white/90">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Longform</div>
                <div className="mt-2 text-2xl font-semibold text-ink-900">{summary.longform}</div>
              </div>
              <div className="data-card p-4 text-center bg-white/90">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">From Plan</div>
                <div className="mt-2 text-2xl font-semibold text-ink-900">{summary.fromPlan}</div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.1fr_1.1fr_1fr]">
          <div className="archive-card p-6 hover-lift">
            <div className="section-title mb-2">Start 01</div>
            <h3 className="text-xl font-semibold text-ink-900">从教案生成课件</h3>
            <p className="mt-2 text-sm text-ink-500 leading-6">
              推荐主入口。先在分析页完成白盒分析与教学方案，再把结果推进为可编辑的课件项目。
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <span className="drawer-handle">白盒分析</span>
              <span className="drawer-handle">教学方案</span>
              <span className="drawer-handle">生成课件</span>
            </div>
            <Link href="/analysis" className="btn-primary mt-6 rounded-full px-5 py-3 text-sm">
              去分析页生成
            </Link>
          </div>

          <div className="archive-card p-6 hover-lift">
            <div className="section-title mb-2">Start 02</div>
            <h3 className="text-xl font-semibold text-ink-900">从空白模板开始</h3>
            <p className="mt-2 text-sm text-ink-500 leading-6">
              适合先做展示骨架，再补充内容。可直接创建幻灯片式或长页面式课件项目。
            </p>
            <div className="mt-6 grid gap-2 sm:grid-cols-2">
              <button onClick={() => handleCreateBlank("slides")} disabled={creating !== null} className="btn-primary rounded-full px-5 py-3 text-sm disabled:opacity-50">
                {creating === "slides" ? '创建中...' : '新建幻灯片'}
              </button>
              <button onClick={() => handleCreateBlank("longform")} disabled={creating !== null} className="btn-secondary rounded-full px-5 py-3 text-sm disabled:opacity-50">
                {creating === "longform" ? '创建中...' : '新建长页面'}
              </button>
            </div>
          </div>

          <div className="archive-surface p-6">
            <div className="section-title mb-2">Continue</div>
            <h3 className="text-xl font-semibold text-ink-900">继续最近项目</h3>
            {summary.latest ? (
              <>
                <div className="mt-4 rounded-2xl bg-white/90 p-4 shadow-soft border border-black/5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="drawer-handle bg-canvas-100 border border-black/5 text-ink-500">{getModeLabel(summary.latest.mode)}</span>
                    <span className="text-xs text-ink-400">{new Date(summary.latest.updated_at).toLocaleDateString('zh-CN')}</span>
                  </div>
                  <h4 className="mt-4 text-lg font-semibold text-ink-900">{summary.latest.title}</h4>
                  <p className="mt-2 text-sm text-ink-500 leading-6">
                    {getSourceLabel(summary.latest.source_type)} · {getStatusLabel(summary.latest.status)}
                  </p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link href={`/courseware/${summary.latest.id}`} className="btn-secondary rounded-full px-4 py-2 text-xs">
                    查看详情
                  </Link>
                  <Link href={`/courseware/${summary.latest.id}/edit`} className="btn-primary rounded-full px-4 py-2 text-xs">
                    继续编辑
                  </Link>
                </div>
              </>
            ) : (
              <p className="mt-3 text-sm text-ink-500 leading-6">当前还没有课件项目。建议从分析页先生成第一份课件。</p>
            )}
          </div>
        </section>

        {loading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="archive-surface p-6 animate-pulse" style={{ animationDelay: `${i * 150}ms` }}>
                <div className="flex justify-between items-start">
                  <div className="flex-1 space-y-3">
                    <div className="h-5 bg-gray-200 rounded-lg w-2/5" />
                    <div className="flex gap-3">
                      <div className="h-5 bg-gray-100 rounded-full w-16" />
                      <div className="h-5 bg-gray-100 rounded-full w-20" />
                    </div>
                  </div>
                  <div className="h-6 bg-gray-100 rounded-full w-16" />
                </div>
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="archive-surface p-12 text-center">
            <div className="mx-auto w-24 h-24 rounded-[28px] bg-canvas-200 flex items-center justify-center mb-6 shadow-soft">
              <svg className="w-12 h-12 text-archive-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <div className="section-title mb-2">No courseware yet</div>
            <h2 className="text-2xl font-semibold text-ink-900 mb-2">暂无教学课件</h2>
            <p className="text-ink-500 mb-8 max-w-sm mx-auto leading-7">
              从分析页生成一份课件，或从空白模板开始建立第一份 HTML 教学课件项目。
            </p>
            <div className="flex justify-center gap-3 flex-wrap">
              <Link href="/analysis" className="btn-primary rounded-full px-5 py-3 text-sm">
                从分析页生成
              </Link>
              <button onClick={() => handleCreateBlank("slides")} disabled={creating !== null} className="btn-secondary rounded-full px-5 py-3 text-sm disabled:opacity-50">
                空白新建
              </button>
            </div>
          </div>
        ) : (
          <section className="space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="section-title mb-2">Courseware Projects</div>
                <h2 className="text-2xl font-semibold text-ink-900">继续你的课件项目</h2>
              </div>
              <p className="text-sm text-ink-500">从这里进入详情、版本、展示配置与编辑工作流。</p>
            </div>
            {projects.map((project, idx) => (
              <div key={project.id} className="archive-card animate-slide-up" style={{ animationDelay: `${idx * 80}ms`, animationFillMode: "both" }}>
                <div className="flex flex-col lg:flex-row lg:items-stretch">
                  <div className="lg:w-24 bg-archive-800 text-white px-5 py-4 lg:py-0 flex lg:flex-col lg:items-center lg:justify-center gap-1">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-white/60">模式</div>
                    <div className="text-2xl leading-none">{getModeIcon(project.mode)}</div>
                    <div className="text-sm font-medium">{getModeLabel(project.mode)}</div>
                  </div>
                  <div className="lg:w-44 px-5 py-4 border-b lg:border-b-0 lg:border-r border-black/5 bg-canvas-100/70">
                    <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">来源</div>
                    <div className="mt-3 text-sm font-medium text-ink-800">{getSourceLabel(project.source_type)}</div>
                    <div className="mt-2 text-xs text-ink-400">更新于 {new Date(project.updated_at).toLocaleDateString("zh-CN")}</div>
                  </div>
                  <div className="flex-1 px-5 py-4 bg-white">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0 flex-1">
                        <Link href={`/courseware/${project.id}`} className="text-lg font-semibold text-ink-900 hover:text-ink-700 transition-colors">
                          {project.title}
                        </Link>
                        <p className="mt-2 text-sm text-ink-500 leading-6">
                          可继续编辑、调整展示配置、提取组件。
                        </p>
                      </div>
                      <div className="flex items-center gap-2 self-start">
                        <span className="drawer-handle bg-white border border-black/5 text-ink-500">{getStatusLabel(project.status)}</span>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-2 pt-4 border-t border-black/5">
                      <Link href={`/courseware/${project.id}`} className="btn-secondary rounded-full px-4 py-2 text-xs">
                        查看详情
                      </Link>
                      <Link href={`/courseware/${project.id}/edit`} className="btn-primary rounded-full px-4 py-2 text-xs">
                        继续编辑
                      </Link>
                      <Link href={`/courseware/${project.id}/present`} className="btn-secondary rounded-full px-4 py-2 text-xs">
                        课堂展示
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </section>
        )}
      </main>
    </div>
  );
}
