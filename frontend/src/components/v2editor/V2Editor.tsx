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
import {
  buildPatchCss,
  exportFileName,
  hasDomPatches,
  injectExportStyle,
  insertPatchId,
  insertWrapperSelector,
  makeFingerprint,
  nextInsertSeq,
  nextOeId,
  normalizePatch,
  patchId,
  stripExportStyle,
  targetLabel,
  type VeInsertPosition,
  type VePatch,
} from "./patches";

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

interface OfficialComponent {
  id: string;
  name: string;
  summary: string | null;
  category: string | null;
  teaching_stage?: string | null;
  render_template_html: string | null;
}

const HISTORY_CAP = 50;

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
  const [components, setComponents] = useState<OfficialComponent[]>([]);

  const [history, setHistory] = useState<VePatch[][]>([[]]);
  const [hIndex, setHIndex] = useState(0);
  const [savedSig, setSavedSig] = useState<string>("");
  const patches = history[hIndex] || [];
  const [unresolved, setUnresolved] = useState<Record<string, string>>({});

  const css = useMemo(() => buildPatchCss(patches), [patches]);
  const domPatches = useMemo(
    () => patches.filter((p) => p.kind === "text" || p.kind === "image" || p.kind === "insert"),
    [patches]
  );
  const patchesRef = useRef<VePatch[]>([]);
  useEffect(() => {
    patchesRef.current = patches;
  }, [patches]);
  const exportResolveRef = useRef<((html: string) => void) | null>(null);

  const sendRpc = useCallback((type: string, payload: Record<string, unknown>) => {
    bridgeRef.current?.send(iframeRef.current?.contentWindow || null, type, payload);
  }, []);

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
        const schema = (v?.editor_schema_json || {}) as { ve_patches?: VePatch[] };
        const html = v?.rendered_html || "";
        const savedPatches = (
          (Array.isArray(schema.ve_patches) ? schema.ve_patches : []) as VePatch[]
        ).map(normalizePatch);
        setSourceHtml(savedPatches.length > 0 ? stripExportStyle(html) : html);
        setSavedSig(JSON.stringify(savedPatches));
        if (savedPatches.length > 0) {
          setHistory([savedPatches]);
          patchesRef.current = savedPatches;
        }
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
    if (loading) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (JSON.stringify(patches) !== savedSig) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [loading, patches, savedSig]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const items = await apiGet<OfficialComponent[]>(
          "/courseware/components?scope=official"
        );
        if (!cancelled)
          setComponents(
            items.filter((c) => (c.render_template_html || "").trim().length > 0)
          );
      } catch {
        // 组件库不可用时静默降级：Inspector 不显示插入区
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const bridge = createHostBridge(channel, (type, payload) => {
      if (type === "ve:ready") {
        setAgentReady(true);
        setPages((payload.pages as VePageInfo[]) || []);
        const cur = patchesRef.current;
        if (cur.length > 0) {
          bridge.send(iframeRef.current?.contentWindow || null, "ve:verify", {
            items: cur.map((p) =>
              p.kind === "insert"
                ? {
                    id: p.id,
                    selector: insertWrapperSelector(p.id),
                    tag: "div",
                    skipDetail: true,
                  }
                : {
                    id: p.id,
                    selector: p.selector,
                    tag: p.fingerprint.tag,
                    childCount: p.fingerprint.childCount,
                    text: p.fingerprint.text,
                  }
            ),
          });
        }
        bridge.send(iframeRef.current?.contentWindow || null, "ve:patches:applyAll", {
          css: buildPatchCss(cur),
          patches: cur.filter((p) => p.kind !== "css"),
        });
      }
      if (type === "ve:pick") {
        setTarget(payload as unknown as VeTarget);
        setRect((payload as { rect: VeRect }).rect);
      }
      if (type === "ve:rect" && payload.rect) {
        setRect(payload.rect as VeRect);
      }
      if (type === "ve:text:commit") {
        const sel = String(payload.selector || "");
        const text = typeof payload.text === "string" ? payload.text : "";
        if (sel) upsertTextRef.current(sel, text);
      }
      if (type === "ve:export:result" && exportResolveRef.current) {
        exportResolveRef.current(String(payload.html || ""));
        exportResolveRef.current = null;
      }
      if (type === "ve:verify:result") {
        const map: Record<string, string> = {};
        for (const r of (payload.results as Array<{ id: string; ok: boolean; reason: string }>) || []) {
          if (!r.ok) map[r.id] = r.reason || "无法定位";
        }
        setUnresolved(map);
      }
    });
    bridgeRef.current = bridge;
    return () => {
      bridge.dispose();
      bridgeRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channel]);

  useEffect(() => {
    if (!agentReady) return;
    sendRpc("ve:patches:applyAll", { css, patches: domPatches });
  }, [agentReady, css, domPatches, sendRpc]);

  const mutatePatches = useCallback(
    (next: VePatch[]) => {
      const cur = history[hIndex] || [];
      const sameShape =
        cur.length === next.length && cur.every((p, i) => p.id === next[i].id);
      if (sameShape) {
        const copy = history.slice();
        copy[hIndex] = next;
        setHistory(copy);
        return;
      }
      const grown = history.slice(0, hIndex + 1).concat([next]);
      const capped =
        grown.length > HISTORY_CAP ? grown.slice(grown.length - HISTORY_CAP) : grown;
      setHistory(capped);
      setHIndex(capped.length - 1);
    },
    [history, hIndex]
  );

  const undo = useCallback(() => setHIndex((i) => Math.max(0, i - 1)), []);
  const redo = useCallback(
    () => setHIndex((i) => Math.min(history.length - 1, i + 1)),
    [history.length]
  );

  const setPickMode = useCallback(
    (enabled: boolean) => {
      setPickOn(enabled);
      sendRpc("ve:pick:set", { enabled });
      if (!enabled) setTarget(null);
    },
    [sendRpc]
  );

  const onStyleChange = useCallback(
    (prop: string, value: string | null) => {
      if (!target) return;
      const pid = patchId(target.selector, "css", prop);
      const exists = patches.find((p) => p.id === pid);
      if (value === null) {
        if (exists) mutatePatches(patches.filter((p) => p.id !== pid));
        return;
      }
      if (exists && exists.value === value) return;
      const next: VePatch = exists
        ? { ...exists, value }
        : {
            id: pid,
            kind: "css",
            selector: target.selector,
            label: targetLabel(target),
            prop,
            value,
            fingerprint: makeFingerprint(target),
          };
      mutatePatches(
        exists ? patches.map((p) => (p.id === pid ? next : p)) : patches.concat([next])
      );
    },
    [target, patches, mutatePatches]
  );

  const selectorTailLabel = useCallback((selector: string) => {
    const tail = selector.split(" > ").pop() || selector;
    return tail.replace(/:nth-of-type\(\d+\)/g, "");
  }, []);

  const upsertTextRef = useRef<(sel: string, text: string) => void>(() => {});

  const upsertTextPatch = useCallback(
    (selector: string, text: string) => {
      const pid = patchId(selector, "text");
      const exists = patches.find((p) => p.id === pid);
      const label =
        target && target.selector === selector
          ? targetLabel(target)
          : `文本 · ${selectorTailLabel(selector)}`;
      if (exists && exists.newText === text) return;
      const next: VePatch = exists
        ? { ...exists, newText: text }
        : {
            id: pid,
            kind: "text",
            selector,
            label,
            newText: text,
            fingerprint:
              target && target.selector === selector
                ? makeFingerprint(target)
                : { tag: selectorTailLabel(selector), childCount: 0, text: "", w: 0, h: 0 },
          };
      mutatePatches(
        exists ? patches.map((p) => (p.id === pid ? next : p)) : patches.concat([next])
      );
    },
    [patches, mutatePatches, target, selectorTailLabel]
  );
  useEffect(() => {
    upsertTextRef.current = upsertTextPatch;
  }, [upsertTextPatch]);

  const onImageReplace = useCallback(
    (selector: string, src: string) => {
      if (!target) return;
      const pid = patchId(selector, "image");
      const exists = patches.find((p) => p.id === pid);
      const next: VePatch = exists
        ? { ...exists, newSrc: src }
        : {
            id: pid,
            kind: "image",
            selector,
            label: targetLabel(target),
            newSrc: src,
            fingerprint: makeFingerprint(target),
          };
      mutatePatches(
        exists ? patches.map((p) => (p.id === pid ? next : p)) : patches.concat([next])
      );
    },
    [target, patches, mutatePatches]
  );

  const onInsertComponent = useCallback(
    (component: OfficialComponent, position: VeInsertPosition) => {
      if (!target) return;
      const next: VePatch = {
        id: insertPatchId(target.selector, nextInsertSeq(patches, target.selector)),
        kind: "insert",
        selector: target.selector,
        label: `插入组件 · ${component.name}`,
        position,
        html: component.render_template_html || "",
        fingerprint: { tag: "div", childCount: 0, text: "", w: 0, h: 0 },
      };
      mutatePatches(patches.concat([next]));
    },
    [target, patches, mutatePatches]
  );

  const onInsertTextBox = useCallback(
    (position: VeInsertPosition) => {
      if (!target) return;
      const oeId = nextOeId(patches, "oe-text");
      const next: VePatch = {
        id: insertPatchId(target.selector, nextInsertSeq(patches, target.selector)),
        kind: "insert",
        selector: target.selector,
        label: `插入文本框 · ${oeId}`,
        position,
        oeId,
        html:
          `<div data-oe-id="${oeId}" style="padding:12px 18px;border:1px dashed var(--line,#d6d2c7);` +
          `border-radius:10px;font-size:20px;line-height:1.7;color:var(--text,#2b2b33)">双击编辑这段文字</div>`,
        fingerprint: { tag: "div", childCount: 0, text: "", w: 0, h: 0 },
      };
      mutatePatches(patches.concat([next]));
    },
    [target, patches, mutatePatches]
  );

  const onInsertImage = useCallback(
    (position: VeInsertPosition, src: string) => {
      if (!target) return;
      const oeId = nextOeId(patches, "oe-img");
      const next: VePatch = {
        id: insertPatchId(target.selector, nextInsertSeq(patches, target.selector)),
        kind: "insert",
        selector: target.selector,
        label: `插入图片 · ${oeId}`,
        position,
        oeId,
        html:
          `<img data-oe-id="${oeId}" src="${src}" alt="插入的图片" ` +
          `style="max-width:100%;border-radius:10px">`,
        fingerprint: { tag: "div", childCount: 0, text: "", w: 0, h: 0 },
      };
      mutatePatches(patches.concat([next]));
    },
    [target, patches, mutatePatches]
  );

  const getExportHtml = useCallback((): Promise<string> => {
    if (!hasDomPatches(patches)) {
      return Promise.resolve(
        patches.length > 0 ? injectExportStyle(sourceHtml, css) : sourceHtml
      );
    }
    return new Promise<string>((resolve) => {
      exportResolveRef.current = resolve;
      sendRpc("ve:export", { css });
      setTimeout(() => {
        if (exportResolveRef.current === resolve) {
          exportResolveRef.current = null;
          resolve(injectExportStyle(sourceHtml, css));
        }
      }, 3000);
    });
  }, [patches, sourceHtml, css, sendRpc]);

  const patchValueFor = useCallback(
    (prop: string) =>
      patches.find((p) => p.prop === prop && p.selector === target?.selector)?.value,
    [patches, target]
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      const typing = el && ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName);
      if (e.key === "Escape") {
        if (pickOn) setPickMode(false);
        else setTarget(null);
        return;
      }
      if ((e.ctrlKey || e.metaKey) && !typing && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pickOn, setPickMode, undo, redo]);

  const handleSaveVersion = useCallback(async () => {
    if (!sourceHtml) return;
    setSaving(true);
    setSavedMsg(null);
    try {
      const htmlOut = await getExportHtml();
      const result = await apiPost<{ version: CoursewareVersion }>(
        `/courseware/${projectId}/versions`,
        {
          editor_schema_json: {
            ...((currentVersion?.editor_schema_json as object) || {}),
            ve_patches: patches,
          },
          rendered_html: htmlOut,
          save_type: "manual_snapshot",
          change_summary:
            patches.length > 0 ? `V2 编辑 · ${patches.length} 处调整` : "V2 编辑器保存",
        }
      );
      setCurrentVersion(result.version);
      setSavedSig(JSON.stringify(patches));
      setSavedMsg("版本已保存");
      setTimeout(() => setSavedMsg(null), 2200);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }, [projectId, sourceHtml, getExportHtml, patches, currentVersion]);

  const handleExport = useCallback(async () => {
    if (!sourceHtml) return;
    const htmlOut = await getExportHtml();
    const blob = new Blob([htmlOut], { type: "text/html;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = exportFileName(project?.title || "courseware");
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  }, [sourceHtml, getExportHtml, project]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center text-slate-400">
        加载 V2 编辑器…
      </div>
    );
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
          <Link
            href={`/courseware/${projectId}`}
            className="text-slate-400 hover:text-slate-700 text-sm flex-shrink-0"
          >
            ←
          </Link>
          <span className="font-medium text-slate-800 truncate">{project.title}</span>
          <span className="hidden sm:inline text-xs text-slate-400">
            v{currentVersion?.version_number || 1} ·{" "}
            {pages.length > 0
              ? `${pages.length} 页`
              : project.mode === "slides"
                ? "幻灯片式"
                : "长页面式"}
          </span>
          <span className="hidden lg:inline rounded-full bg-slate-100 border border-slate-200 px-2 py-0.5 text-[10px] text-slate-500">
            AI 生成内容 · 请核对
          </span>
          {patches.length > 0 && (
            <span className="rounded-full bg-blue-50 border border-blue-200 px-2 py-0.5 text-[10px] text-blue-700">
              {patches.length} 处调整
            </span>
          )}
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
          <div className="flex rounded border border-slate-200 overflow-hidden">
            <button
              onClick={undo}
              disabled={hIndex === 0}
              className="px-2.5 py-1 text-xs bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              title="撤销 (Ctrl+Z)"
            >
              撤销
            </button>
            <button
              onClick={redo}
              disabled={hIndex >= history.length - 1}
              className="px-2.5 py-1 text-xs bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40 border-l border-slate-200"
              title="重做 (Ctrl+Shift+Z)"
            >
              重做
            </button>
          </div>
          {savedMsg && <span className="text-xs text-emerald-600">{savedMsg}</span>}
          <Link
            href={`/courseware/${projectId}/edit`}
            className="rounded-full bg-slate-100 px-4 py-1.5 text-xs text-slate-600 hover:bg-slate-200"
          >
            V1 编辑器
          </Link>
          <button
            onClick={() => void handleExport()}
            disabled={!sourceHtml}
            className="rounded-full bg-slate-100 px-4 py-1.5 text-xs text-slate-600 hover:bg-slate-200 disabled:opacity-50"
          >
            导出 HTML
          </button>
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

        {pickOn && !target && (
          <div className="absolute left-1/2 top-4 -translate-x-1/2 z-20 rounded-full bg-blue-600/90 px-4 py-1.5 text-xs text-white shadow">
            点击课件中的任意元素开始编辑
          </div>
        )}

        {target && (
          <Inspector
            key={target.selector}
            target={target}
            patchValue={patchValueFor}
            onStyleChange={onStyleChange}
            onStartTextEdit={(sel) => sendRpc("ve:text:edit", { selector: sel })}
            onImageReplace={onImageReplace}
            components={components}
            onInsertComponent={onInsertComponent}
            onInsertTextBox={onInsertTextBox}
            onInsertImage={onInsertImage}
            onSelectChain={(node) => sendRpc("ve:pick:goto", { selector: node.selector })}
            onClose={() => setTarget(null)}
          />
        )}

        {patches.length > 0 && (
          <div className="absolute right-4 bottom-4 z-30 w-80 rounded-xl border border-slate-200 bg-white shadow-xl">
            <div className="border-b border-slate-100 px-4 py-2.5 text-[10px] uppercase tracking-widest text-slate-400">
              调整记录（保存后生效于展示与导出）
            </div>
            <ul className="max-h-56 overflow-y-auto px-2 py-2 space-y-1">
              {patches.map((p) => (
                <li
                  key={p.id}
                  className="group flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-50"
                >
                  <div className="min-w-0 flex-1">
                    <span className="text-xs text-slate-700 truncate">{p.label}</span>
                    {p.kind === "text" ? (
                      <span className="ml-1.5 text-[11px] text-slate-400">
                        文本：{(p.newText || "").slice(0, 24) || "（空）"}
                        {(p.newText || "").length > 24 ? "…" : ""}
                      </span>
                    ) : p.kind === "image" ? (
                      <span className="ml-1.5 text-[11px] text-slate-400">图片已替换</span>
                    ) : p.kind === "insert" ? (
                      <span className="ml-1.5 text-[11px] text-slate-400">
                        {p.position === "append" ? "插入内部末尾" : p.position === "before" ? "插入之前" : "插入之后"}
                      </span>
                    ) : (
                      <span className="ml-1.5 text-[11px] text-slate-400 font-mono">
                        {p.prop}: {p.value}
                      </span>
                    )}
                    {unresolved[p.id] && (
                      <span
                        className="ml-1.5 rounded bg-amber-50 px-1 py-0.5 text-[10px] text-amber-700"
                        title={unresolved[p.id]}
                      >
                        ⚠ {unresolved[p.id]}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => mutatePatches(patches.filter((x) => x.id !== p.id))}
                    className="opacity-0 group-hover:opacity-100 text-[11px] text-slate-400 hover:text-red-500 flex-shrink-0"
                  >
                    移除
                  </button>
                </li>
              ))}
            </ul>
          </div>
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
