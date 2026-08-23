"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api";

interface CoursewareProject {
  id: string;
  title: string;
  mode: string;
  source_type: string;
  status: string;
  current_version_id: string | null;
  source_meta?: { generated_by?: string } | null;
}

interface CoursewareVersion {
  id: string;
  project_id: string;
  version_number: number;
  save_type: string;
  editor_schema_json: unknown;
  rendered_html: string | null;
  change_summary: string | null;
  created_at: string;
}

export default function CoursewareEditPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const editorReadyRef = useRef(false);
  const editorStateRef = useRef<{ rendered_html?: string; editor_schema_json?: unknown }>({});

  const [project, setProject] = useState<CoursewareProject | null>(null);
  const [currentVersion, setCurrentVersion] = useState<CoursewareVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await apiGet<{
        id: string;
        title: string;
        mode: string;
        source_type: string;
        status: string;
        current_version_id: string | null;
        source_meta?: { generated_by?: string } | null;
        versions: CoursewareVersion[];
      }>(`/courseware/${projectId}`);
      setProject(data);
      const versions = data.versions || [];
      if (versions.length > 0) setCurrentVersion(versions[0]);
      return data;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "加载课件失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const sendToEditor = useCallback((msg: unknown) => {
    if (iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage(msg, window.location.origin);
    }
  }, []);

  const handleSaveVersion = useCallback(async () => {
    if (!projectId) return;
    const latestState = editorStateRef.current;
    setSaving(true);
    setSavedMsg(null);
    try {
      const result = await apiPost<{ project: CoursewareProject; version: CoursewareVersion }>(
        `/courseware/${projectId}/versions`,
        {
          editor_schema_json: latestState.editor_schema_json || currentVersion?.editor_schema_json || {},
          rendered_html: latestState.rendered_html || currentVersion?.rendered_html || "",
          save_type: "manual_snapshot",
          change_summary: "手动保存版本",
        }
      );
      setCurrentVersion(result.version);
      setSavedMsg("版本已保存");
      setTimeout(() => setSavedMsg(null), 2200);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }, [projectId, currentVersion]);

  const handleSaveAsComponent = useCallback(async (payload: { name?: string; html_snippet?: string; tag?: string; teaching_stage?: string | null }) => {
    if (!payload.html_snippet) return;
    try {
      await apiPost("/courseware/components", {
        name: payload.name || (payload.tag ? `${payload.tag} 组件` : "自定义组件"),
        slug: `comp-${Date.now().toString(36)}`,
        summary: "从课件编辑器中提取",
        category: payload.teaching_stage || null,
        teaching_stage: payload.teaching_stage || null,
        scope: "personal",
        render_template_html: payload.html_snippet,
        mode_support: "both",
        is_publishable: false,
        community_status: "draft",
      });
      setSavedMsg("已保存为我的组件");
      setTimeout(() => setSavedMsg(null), 2200);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "保存组件失败");
    }
  }, []);

  useEffect(() => {
    void loadProject();
  }, [loadProject]);

  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (!e.data?.type) return;
      switch (e.data.type) {
        case "editor:ready":
          editorReadyRef.current = true;
          if (currentVersion && project) {
            sendToEditor({
              type: "editor:load",
              payload: {
                rendered_html: currentVersion.rendered_html || "",
                editor_schema_json: currentVersion.editor_schema_json,
                project_id: projectId,
                version_id: currentVersion.id,
                mode: project.mode || "slides",
                title: project.title || "教学课件",
              },
            });
          }
          break;
        case "editor:state":
          editorStateRef.current = e.data.payload || {};
          break;
        case "editor:requestSave":
          void handleSaveVersion();
          break;
        case "editor:saveAsComponent":
          void handleSaveAsComponent(e.data.payload);
          break;
        default:
          break;
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [currentVersion, project, projectId, sendToEditor, handleSaveVersion, handleSaveAsComponent]);

  if (loading) {
    return (
      <div className="h-screen desk-wash flex items-center justify-center">
        <div className="animate-pulse text-ink-400">加载编辑器...</div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="h-screen desk-wash flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || "课件项目未找到"}</p>
          <Link href="/history" className="text-ink-700 hover:underline text-sm">返回历史记录</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen desk-wash flex flex-col">
      <header className="flex-shrink-0 border-b border-black/5 bg-white/75 backdrop-blur-xl">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <Link href={`/courseware/${projectId}`} className="text-sm text-ink-500 hover:text-ink-700 inline-flex items-center gap-1.5">
                <span>&larr;</span>
                返回课件详情
              </Link>
              <div className="mt-2 section-title">Courseware Workbench</div>
              <h1 className="mt-2 text-2xl font-semibold text-ink-900">{project.title}</h1>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="drawer-handle">{project.mode === "slides" ? "幻灯片式" : "长页面式"}</span>
                <span className="drawer-handle bg-white border border-black/5 text-ink-500">{project.status === "in_editing" ? "编辑中" : project.status}</span>
                {currentVersion && <span className="drawer-handle bg-sage-100 border border-sage-200 text-ink-700">当前版本 v{currentVersion.version_number}</span>}
                {project.source_meta?.generated_by === "template_fallback" && (
                  <span className="drawer-handle bg-amber-50 border border-amber-300 text-amber-800">简化版生成（AI 完整生成暂不可用）</span>
                )}
                {project.source_meta?.generated_by === "llm_html" && (
                  <span className="drawer-handle bg-sage-100 border border-sage-200 text-ink-700">AI 生成</span>
                )}
              </div>
            </div>
            <div className="grid gap-2 sm:grid-cols-3 lg:w-[430px]">
              <div className="data-card p-4 bg-white/90 text-center">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Workspace</div>
                <div className="mt-2 text-sm font-semibold text-ink-900">编辑工作区</div>
              </div>
              <div className="data-card p-4 bg-white/90 text-center">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Version</div>
                <div className="mt-2 text-sm font-semibold text-ink-900">{currentVersion ? `v${currentVersion.version_number}` : '初始版'}</div>
              </div>
              <div className="data-card p-4 bg-white/90 text-center">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Next</div>
                <div className="mt-2 text-sm font-semibold text-ink-900">课堂展示</div>
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex flex-wrap gap-2 text-xs text-ink-500">
              <span className="drawer-handle bg-white border border-black/5 text-ink-500">选择元素 → 编辑属性 → 保存版本</span>
              <span className="drawer-handle bg-white border border-black/5 text-ink-500">支持提取为个人组件</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {savedMsg && <span className="text-xs text-emerald-600">{savedMsg}</span>}
              <Link href={`/courseware/${projectId}`} className="btn-secondary rounded-full px-4 py-2 text-xs">查看项目</Link>
              <Link href={`/courseware/${projectId}/present`} className="btn-secondary rounded-full px-4 py-2 text-xs">课堂展示</Link>
              <button
                onClick={() => void handleSaveVersion()}
                disabled={saving}
                className="btn-primary rounded-full px-5 py-2.5 text-xs disabled:opacity-50"
              >
                {saving ? "保存中..." : "保存版本"}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 p-4 sm:p-5 overflow-hidden">
        <div className="h-full max-w-[1600px] mx-auto rounded-[28px] border border-white/50 bg-white/55 backdrop-blur-sm shadow-card overflow-hidden">
          <div className="h-10 border-b border-black/5 bg-white/75 px-4 flex items-center justify-between text-xs text-ink-500">
            <div className="flex items-center gap-2">
              <span className="section-title mb-0">课件精修</span>
              <span className="drawer-handle bg-canvas-100 border border-black/5 text-ink-500">修改可保存为新版本</span>
            </div>
            <span>{project.mode === "slides" ? "幻灯片编辑" : "长页编辑"}</span>
          </div>
          <iframe
            ref={iframeRef}
            src="/editor/index.html"
            className="w-full h-[calc(100%-2.5rem)] border-0 bg-transparent"
            title="课件编辑器"
            sandbox="allow-same-origin allow-scripts allow-downloads allow-forms allow-modals"
          />
        </div>
      </div>
    </div>
  );
}
