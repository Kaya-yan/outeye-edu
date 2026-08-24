"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api";
import {
  createHostBridge,
  type HostBridge,
  type VePageInfo,
  type VeRect,
  type VeTarget,
} from "./rpc";
import { injectAgent } from "./pickAgent";
import Inspector from "./Inspector";

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
  version_number: number;
  save_type: string;
  editor_schema_json: unknown;
  rendered_html: string | null;
  change_summary: string | null;
  created_at: string;
}

export default function V2Editor({ projectId }: { projectId: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const bridgeRef = useRef<HostBridge | null>(null);
  const channel = useMemo(
    () => `ve-${Math.random().toString(36).slice(2)}-${Date.now().toString(36)}`,
    []
  );

  const [project, setProject] = useState<CoursewareProject | null>(null);
  const [currentVersion, setCurrentVersion] = useState<CoursewareVersion | null>(null);
  const [sourceHtml, setSourceHtml] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pickOn, setPickOn] = useState(false);
  const [agentReady, setAgentReady] = useState(false);
  const [pages, setPages] = useState<VePageInfo[]>([]);
  const [target, setTarget] = useState<VeTarget | null>(null);
  const [rect, setRect] = useState<VeRect | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiGet<
          CoursewareProject & { versions: CoursewareVersion[] }
        >(`/courseware/${projectId}`);
        if (cancelled) return;
        setProject(data);
        const v = data.versions?.[0] || null;
        setCurrentVersion(v);
        setSourceHtml(v?.rendered_html || "");
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载课件失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  useEffect(() => {
    const bridge = createHostBridge(channel, (type, payload) => {
      if (type === "ve:ready") {
        setAgentReady(true);
        setPages((payload.pages as VePageInfo[]) || []);
      }
      if (type === "ve:pick") {
        setTarget(payload as unknown as VeTarget);
        setRect((payload as { rect: VeRect }).rect);
      }
      if (type === "ve:rect" && payload.rect) {
        setRect(payload.rect as VeRect);
      }
    });
    bridgeRef.current = bridge;
    return () => {
      bridge.dispose();
      bridgeRef.current = null;
    };
  }, [channel]);

  const setPickMode = useCallback((enabled: boolean) => {
    setPickOn(enabled);
    bridgeRef.current?.send(iframeRef.current?.contentWindow || null, "ve:pick:set", { enabled });
    if (!enabled) setTarget(null);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (pickOn) setPickMode(false);
        else setTarget(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pickOn, setPickMode]);

  const handleSaveVersion = useCallback(async () => {
    if (!sourceHtml) return;
    setSaving(true);
    setSavedMsg(null);
    try {
      const result = await apiPost<{ version: CoursewareVersion }>(
        `/courseware/${projectId}/versions`,
        {
          editor_schema_json: currentVersion?.editor_schema_json || {},
          rendered_html: sourceHtml,
          save_type: "manual_snapshot",
          change_summary: "V2 编辑器保存",
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
  }, [projectId, sourceHtml, currentVersion]);

  if (loading) {
    return <div className="h-screen flex items-center justify-center text-slate-400">加载 V2 编辑器…</div>;
  }

  if (error || !project) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || "课件项目未找到"}</p>
          <Link href="/history" className="text-sm text-slate-500 hover:underline">
            返回历史记录
          </Link>
        </div>
      </div>
    );
  }

  const srcDoc = sourceHtml ? injectAgent(sourceHtml, channel) : "";
  const overlayLabel = target
    ? `${target.tag}${target.component ? ` · ${target.component}` : ""}`
    : "";

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <header className="flex-shrink-0 h-12 border-b border-slate-200 bg-white flex items-center justify-between px-4 gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Link href={`/courseware/${projectId}`} className="text-slate-400 hover:text-slate-700 text-sm flex-shrink-0">
            ←
          </Link>
          <span className="font-medium text-slate-800 truncate">{project.title}</span>
          <span className="hidden sm:inline text-xs text-slate-400">
            v{currentVersion?.version_number || 1} · {pages.length > 0 ? `${pages.length} 页` : project.mode === "slides" ? "幻灯片式" : "长页面式"}
          </span>
          {project.source_meta?.generated_by === "template_fallback" && (
            <span className="hidden md:inline rounded-full bg-amber-50 border border-amber-300 px-2 py-0.5 text-[10px] text-amber-800">
              简化版生成
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPickMode(!pickOn)}
            className={`rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${
              pickOn
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {pickOn ? "拾取中 · 点击页面元素（Esc 退出）" : "选取元素"}
          </button>
          {savedMsg && <span className="text-xs text-emerald-600">{savedMsg}</span>}
          <Link
            href={`/courseware/${projectId}/edit`}
            className="rounded-full bg-slate-100 px-4 py-1.5 text-xs text-slate-600 hover:bg-slate-200"
          >
            V1 编辑器
          </Link>
          <button
            onClick={() => void handleSaveVersion()}
            disabled={saving || !sourceHtml}
            className="rounded-full bg-blue-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "保存中…" : "保存版本"}
          </button>
        </div>
      </header>

      <main className="flex-1 relative overflow-hidden">
        {srcDoc ? (
          <iframe
            ref={iframeRef}
            srcDoc={srcDoc}
            title="课件渲染"
            className="absolute inset-0 w-full h-full border-0 bg-white"
            sandbox="allow-scripts allow-downloads"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-400">
            当前版本无 HTML 内容
          </div>
        )}

        {rect && rect.w > 0 && (
          <div
            className="pointer-events-none absolute z-20 rounded-sm border-2 border-blue-600"
            style={{
              left: rect.x,
              top: rect.y,
              width: rect.w,
              height: rect.h,
              boxShadow: "0 0 0 9999px rgba(15, 23, 42, 0.08)",
            }}
          >
            <span
              className="absolute left-0 rounded-t bg-blue-600 px-1.5 py-0.5 text-[10px] font-medium text-white whitespace-nowrap"
              style={{ top: -20 }}
            >
              {overlayLabel}
            </span>
          </div>
        )}

        {target && (
          <Inspector
            target={target}
            onSelectChain={(node) =>
              bridgeRef.current?.send(iframeRef.current?.contentWindow || null, "ve:pick:goto", {
                selector: node.selector,
              })
            }
            onClose={() => setTarget(null)}
          />
        )}

        {!agentReady && srcDoc && (
          <div className="absolute left-1/2 top-4 -translate-x-1/2 rounded-full bg-slate-800/80 px-4 py-1.5 text-xs text-white">
            正在连接渲染引擎…
          </div>
        )}
      </main>
    </div>
  );
}
