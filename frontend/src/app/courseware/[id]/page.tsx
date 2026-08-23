"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiGet, apiPost, apiRequest } from "@/lib/api";

interface CoursewareProject {
  id: string;
  title: string;
  mode: string;
  source_type: string;
  source_plan_id: string | null;
  status: string;
  source_meta: unknown;
  presentation_profile_id: string | null;
  created_at: string;
  updated_at: string;
}

interface CoursewareVersion {
  id: string;
  project_id: string;
  version_number: number;
  save_type: string;
  rendered_html: string | null;
  editor_schema_json: unknown;
  change_summary: string | null;
  created_at: string;
}

interface PresentationProfile {
  id: string;
  mode: string;
  name: string;
}

interface ExportArtifactItem {
  id: string;
  format: string;
  file_name: string;
  generated_at: string;
  download_url: string;
  extra_data?: { content_count?: number; fallback?: boolean };
}

export default function CoursewareDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [project, setProject] = useState<CoursewareProject | null>(null);
  const [versions, setVersions] = useState<CoursewareVersion[]>([]);
  const [profiles, setProfiles] = useState<PresentationProfile[]>([]);
  const [artifacts, setArtifacts] = useState<ExportArtifactItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [extractingVid, setExtractingVid] = useState<string | null>(null);
  const [extractedMsg, setExtractedMsg] = useState<string | null>(null);

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await apiGet<{
        id: string;
        title: string;
        mode: string;
        source_type: string;
        source_plan_id: string | null;
        status: string;
        source_meta: unknown;
        presentation_profile_id: string | null;
        created_at: string;
        updated_at: string;
        versions: CoursewareVersion[];
        presentation_profiles: PresentationProfile[];
        artifacts?: ExportArtifactItem[];
      }>(`/courseware/${projectId}`);
      setProject(data);
      setVersions(data.versions || []);
      setProfiles(data.presentation_profiles || []);
      setArtifacts(data.artifacts || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "加载课件项目失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void loadProject();
  }, [loadProject]);

  const handleExtractAsComponent = async (v: CoursewareVersion) => {
    if (!projectId) return;
    setExtractingVid(v.id);
    setExtractedMsg(null);
    try {
      const name = window.prompt("组件名称：", `${project?.title || "课件"} · v${v.version_number}`);
      if (!name) {
        setExtractingVid(null);
        return;
      }
      await apiPost("/courseware/components", {
        name,
        slug: `extracted-${Date.now().toString(36)}`,
        summary: `从课件 ${project?.title || ""} v${v.version_number} 提取`,
        category: null,
        teaching_stage: null,
        scope: "personal",
        render_template_html: v.rendered_html || "",
        mode_support: project?.mode || "both",
        is_publishable: false,
        community_status: "draft",
      });
      setExtractedMsg(`已保存：${name}`);
      setTimeout(() => setExtractedMsg(null), 2500);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "提取组件失败");
    } finally {
      setExtractingVid(null);
    }
  };

  const handleDownloadArtifact = async (a: ExportArtifactItem) => {
    try {
      const resp = await apiRequest("GET", a.download_url);
      if (!resp.ok) throw new Error("下载失败");
      const blob = await resp.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = a.file_name || `courseware.${a.format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(link.href);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "下载产物失败");
    }
  };

  const getModeLabel = (mode: string) => (mode === "slides" ? "幻灯片式" : "长页面式");
  const getStatusLabel = (status: string) => {
    switch (status) {
      case "draft":
        return "草稿";
      case "in_editing":
        return "编辑中";
      case "ready_to_present":
        return "可展示";
      case "archived":
        return "已归档";
      default:
        return status;
    }
  };

  const latestVersion = versions[0] || null;
  const latestProfile = profiles[0] || null;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-ink-400">加载中...</div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || "课件项目未找到"}</p>
          <Link href="/history" className="text-ink-700 hover:underline text-sm">
            返回历史记录
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="max-w-7xl mx-auto brand-surface px-6 py-7 sm:px-8 sm:py-8 mb-6">
        <Link href="/history" className="text-sm text-ink-500 hover:text-ink-700 mb-2 inline-block">
          &larr; 返回历史记录
        </Link>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between mt-2">
          <div>
            <div className="section-title mb-2">Courseware Archive</div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-ink-900">{project.title}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-3">
              <span className="drawer-handle">{getModeLabel(project.mode)}</span>
              <span className="drawer-handle bg-white border border-black/5 text-ink-500">{getStatusLabel(project.status)}</span>
              {project.source_type === "from_plan" && <span className="drawer-handle bg-sage-100 border border-sage-200 text-ink-600">从教案生成</span>}
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button onClick={() => router.push(`/courseware/${projectId}/edit`)} className="btn-primary rounded-full px-5 py-3 text-sm">
              进入编辑器
            </button>
            <button onClick={() => router.push(`/courseware/${projectId}/present`)} className="btn-secondary rounded-full px-5 py-3 text-sm">
              课堂展示
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto space-y-6">
        <section className="grid gap-4 lg:grid-cols-3">
          <div className="archive-surface p-6 hover-lift">
            <div className="section-title mb-2">Next Action</div>
            <h2 className="text-xl font-semibold text-ink-900">继续生产</h2>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link href={`/courseware/${projectId}/edit`} className="btn-primary rounded-full px-4 py-2 text-xs">
                去编辑
              </Link>
              <Link href={`/courseware/${projectId}/present`} className="btn-secondary rounded-full px-4 py-2 text-xs">
                去展示
              </Link>
            </div>
          </div>

          <div className="archive-surface p-6 hover-lift">
            <div className="section-title mb-2">Current Version</div>
            <h2 className="text-xl font-semibold text-ink-900">版本栈</h2>
            <div className="mt-5 flex items-end justify-between gap-4">
              <div>
                <div className="text-3xl font-semibold text-ink-900">v{latestVersion?.version_number || 1}</div>
                <div className="text-xs text-ink-400 mt-1">{latestVersion?.change_summary || "初始版本"}</div>
              </div>
              <span className="drawer-handle bg-canvas-100 border border-black/5 text-ink-500">{versions.length} 个快照</span>
            </div>
          </div>

          <div className="archive-surface p-6 hover-lift">
            <div className="section-title mb-2">Presentation</div>
            <h2 className="text-xl font-semibold text-ink-900">展示配置</h2>
            <div className="mt-5 flex flex-wrap gap-2">
              <span className="drawer-handle bg-white border border-black/5 text-ink-500">{latestProfile?.name || "默认展示配置"}</span>
              <span className="drawer-handle">{getModeLabel(latestProfile?.mode || project.mode)}</span>
            </div>
          </div>
        </section>

        {extractedMsg && (
          <div className="rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {extractedMsg}
          </div>
        )}

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="archive-surface p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="section-title mb-2">Version Stack</div>
                  <h2 className="text-xl font-semibold text-ink-900">版本历史</h2>
                </div>
              </div>
              {versions.length === 0 ? (
                <p className="text-sm text-ink-500">尚无保存版本</p>
              ) : (
                <div className="space-y-3">
                  {versions.map((v) => (
                    <div key={v.id} className="rounded-2xl border border-black/5 bg-white/90 px-4 py-4 shadow-soft">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <div className="text-sm font-semibold text-ink-900">v{v.version_number}</div>
                          <div className="text-xs text-ink-400 mt-1">{v.change_summary || "无说明"}</div>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-ink-400">{new Date(v.created_at).toLocaleString("zh-CN")}</span>
                          <button
                            onClick={() => handleExtractAsComponent(v)}
                            disabled={extractingVid === v.id}
                            className="drawer-handle bg-canvas-100 border border-black/5 text-ink-600 disabled:opacity-50"
                          >
                            {extractingVid === v.id ? "提取中..." : "提取为组件"}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="archive-surface p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="section-title mb-2">Artifacts</div>
                  <h2 className="text-xl font-semibold text-ink-900">生成产物</h2>
                </div>
              </div>
              {artifacts.length === 0 ? (
                <p className="text-sm text-ink-500">尚无 PPT / Word 产物（可在分析页教案确认后生成）</p>
              ) : (
                <div className="space-y-3">
                  {artifacts.map((a) => (
                    <div key={a.id} className="rounded-2xl border border-black/5 bg-white/90 px-4 py-4 shadow-soft">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <div className="text-sm font-semibold text-ink-900">
                            {a.file_name || `courseware.${a.format}`}
                            {a.extra_data?.fallback && (
                              <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-800">
                                简化版生成
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-ink-400 mt-1">
                            {a.format.toUpperCase()} · {new Date(a.generated_at).toLocaleString("zh-CN")}
                            {a.extra_data?.content_count ? ` · ${a.extra_data.content_count} ${a.format === "docx" ? "节" : "页"}` : ""}
                          </div>
                        </div>
                        <button
                          onClick={() => handleDownloadArtifact(a)}
                          className="btn-secondary rounded-full px-4 py-2 text-xs"
                        >
                          下载
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="archive-surface p-6">
              <div className="section-title mb-2">Project Meta</div>
              <h2 className="text-xl font-semibold text-ink-900 mb-4">项目信息</h2>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-400">课件模式</dt>
                  <dd className="text-ink-900 font-medium text-right">{getModeLabel(project.mode)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-400">来源</dt>
                  <dd className="text-ink-900 text-right">
                    {project.source_type === "from_plan"
                      ? "教案生成"
                      : project.source_type === "imported_html"
                        ? "导入 HTML"
                        : "空白模板"}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-400">创建时间</dt>
                  <dd className="text-ink-900 text-right">{new Date(project.created_at).toLocaleString("zh-CN")}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-400">版本数</dt>
                  <dd className="text-ink-900 text-right">{versions.length}</dd>
                </div>
              </dl>
            </div>

            {profiles.length > 0 && (
              <div className="archive-surface p-6">
                <div className="section-title mb-2">Presentation Profiles</div>
                <h2 className="text-xl font-semibold text-ink-900 mb-4">展示配置</h2>
                <div className="space-y-2">
                  {profiles.map((p) => (
                    <div key={p.id} className="flex items-center justify-between rounded-xl bg-white/90 px-3 py-2 shadow-soft text-sm">
                      <span className="text-ink-700">{p.name}</span>
                      <span className="text-xs text-ink-400">{getModeLabel(p.mode)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
