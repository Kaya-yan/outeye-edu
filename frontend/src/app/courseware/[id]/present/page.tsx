"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiGet } from "@/lib/api";

interface CoursewareProject {
  id: string;
  title: string;
  mode: string;
  status: string;
}

interface CoursewareVersion {
  id: string;
  version_number: number;
  rendered_html: string | null;
}

export default function CoursewarePresentPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const totalSlides = useRef(1);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [project, setProject] = useState<CoursewareProject | null>(null);
  const [renderedHtml, setRenderedHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(1);
  const [isBlackout, setIsBlackout] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [timerRunning, setTimerRunning] = useState(false);
  const [hideUI, setHideUI] = useState(false);
  const [sections, setSections] = useState<string[]>([]);
  const [activeSection, setActiveSection] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await apiGet<{
        id: string;
        title: string;
        mode: string;
        status: string;
        versions: CoursewareVersion[];
      }>(`/courseware/${projectId}`);
      setProject(data);
      const versions = data.versions || [];
      if (versions.length > 0) {
        setRenderedHtml(versions[0].rendered_html);
      }
    } catch (e: unknown) {
      setLoadError(e instanceof Error ? e.message : "加载课件失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void loadProject();
  }, [loadProject]);

  const toggleFullscreen = useCallback(() => {
    if (!isFullscreen) {
      document.documentElement.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  }, [isFullscreen]);

  const toggleTimer = useCallback(() => {
    if (timerRunning) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      setTimerRunning(false);
    } else {
      timerRef.current = setInterval(() => setTimerSeconds((s) => s + 1), 1000);
      setTimerRunning(true);
    }
  }, [timerRunning]);

  const triggerReveal = useCallback(() => {
    if (!iframeRef.current?.contentWindow) return;
    try {
      const doc = iframeRef.current.contentDocument || iframeRef.current.contentWindow.document;
      const allReveal = doc.querySelectorAll("[data-reveal]");
      let found = false;
      for (let i = 0; i < allReveal.length; i++) {
        const el = allReveal[i] as HTMLElement;
        if (el.dataset.revealState !== "shown") {
          el.style.display = "block";
          el.dataset.revealState = "shown";
          found = true;
          break;
        }
      }
      if (!found) setCurrentSlide((prev) => Math.min(prev + 1, totalSlides.current));
    } catch {
      setCurrentSlide((prev) => Math.min(prev + 1, totalSlides.current));
    }
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") {
        e.preventDefault();
        setCurrentSlide((prev) => Math.min(prev + 1, totalSlides.current));
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        setCurrentSlide((prev) => Math.max(prev - 1, 1));
      } else if (e.key === " ") {
        e.preventDefault();
        triggerReveal();
      } else if (e.key === "Escape") {
        if (isFullscreen) {
          document.exitFullscreen?.();
          setIsFullscreen(false);
        }
      } else if (e.key === "b" || e.key === "B") {
        setIsBlackout((prev) => !prev);
      } else if (e.key === "n" || e.key === "N") {
        setShowNotes((prev) => !prev);
      } else if (e.key === "t" || e.key === "T") {
        toggleTimer();
      } else if (e.key === "h" || e.key === "H") {
        setHideUI((prev) => !prev);
      } else if (e.key === "f" || e.key === "F") {
        toggleFullscreen();
      } else if (e.key === "Home") {
        setCurrentSlide(1);
      } else if (e.key === "End") {
        setCurrentSlide(totalSlides.current);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreen, toggleFullscreen, toggleTimer, triggerReveal]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const extractSections = useCallback(() => {
    if (project?.mode !== "longform") return;
    try {
      const ifr = iframeRef.current;
      if (!ifr || !ifr.contentWindow) return;
      const doc = ifr.contentDocument || ifr.contentWindow.document;
      const els = doc.querySelectorAll("[data-section]");
      const names: string[] = [];
      els.forEach((el) => {
        names.push(el.getAttribute("data-section") || el.textContent?.trim().substring(0, 20) || "");
      });
      setSections(names);
    } catch {
      // ignore
    }
  }, [project?.mode]);

  const scrollToSection = useCallback((idx: number) => {
    if (!iframeRef.current?.contentWindow) return;
    try {
      const doc = iframeRef.current.contentDocument || iframeRef.current.contentWindow.document;
      const els = doc.querySelectorAll("[data-section]");
      const target = els[idx];
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveSection(idx);
    } catch {
      // ignore
    }
  }, []);

  const resetTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setTimerSeconds(0);
    setTimerRunning(false);
  };

  const formatTime = (totalSec: number) => {
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-ink-900 flex items-center justify-center">
        <div className="animate-pulse text-white/50">加载展示端...</div>
      </div>
    );
  }

  if (loadError || !project) {
    return (
      <div className="min-h-screen bg-ink-900 flex items-center justify-center">
        <div className="text-center text-white/70">
          <p className="mb-4">{loadError || "课件未找到"}</p>
          <Link href="/history" className="text-white/80 hover:underline text-sm">返回历史记录</Link>
        </div>
      </div>
    );
  }

  const toolbarClasses = `flex-shrink-0 bg-ink-900/88 backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-4 sm:px-5 h-12 transition-opacity duration-300 ${
    isFullscreen ? "opacity-0 hover:opacity-100 absolute top-0 left-0 right-0 z-10" : ""
  } ${hideUI && isFullscreen ? "pointer-events-none" : ""}`;

  const footerClasses = `flex-shrink-0 bg-ink-900/88 backdrop-blur-xl border-t border-white/10 flex items-center justify-between px-4 sm:px-5 h-10 transition-opacity duration-300 ${
    isFullscreen ? "opacity-0 hover:opacity-100 absolute bottom-0 left-0 right-0 z-10" : ""
  } ${hideUI && isFullscreen ? "pointer-events-none" : ""}`;

  return (
    <div className="min-h-screen flex flex-col bg-ink-900 relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute right-[-6%] top-[-12%] h-72 w-72 rounded-full bg-primary-300/10 blur-3xl" />
        <div className="absolute left-[-8%] bottom-[8%] h-64 w-64 rounded-full bg-sage-300/10 blur-3xl" />
      </div>

      <div className={toolbarClasses}>
        <div className="flex items-center gap-3 min-w-0">
          <Link href={`/courseware/${projectId}`} className="text-xs text-white/55 hover:text-white/80 transition-colors">&larr;</Link>
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.18em] text-white/35">Presentation Mode</div>
            <div className="text-sm text-white/90 truncate">{project.title}</div>
          </div>
          <span className="drawer-handle bg-white/10 border border-white/10 text-white/70">
            {project.mode === "slides" ? "幻灯片" : "长页面"}
          </span>
          {timerRunning && (
            <span className="drawer-handle bg-warning-400/20 border border-warning-400/20 text-warning-400 font-mono">
              {formatTime(timerSeconds)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => { resetTimer(); toggleTimer(); }} className={`text-xs px-3 py-1.5 rounded-full transition-colors ${timerRunning ? "bg-white/12 text-white" : "text-white/55 hover:text-white hover:bg-white/8"}`}>
            {timerRunning ? "停止计时" : "计时"}
          </button>
          <button onClick={() => setShowNotes(!showNotes)} className={`text-xs px-3 py-1.5 rounded-full transition-colors ${showNotes ? "bg-white/14 text-white" : "text-white/55 hover:text-white hover:bg-white/8"}`}>备注</button>
          <button onClick={() => setIsBlackout(!isBlackout)} className={`text-xs px-3 py-1.5 rounded-full transition-colors ${isBlackout ? "bg-white/14 text-white" : "text-white/55 hover:text-white hover:bg-white/8"}`}>{isBlackout ? "恢复" : "黑屏"}</button>
          <button onClick={toggleFullscreen} className="text-xs px-3 py-1.5 rounded-full text-white/55 hover:text-white hover:bg-white/8 transition-colors">{isFullscreen ? "退出" : "全屏"}</button>
        </div>
      </div>

      {showNotes && !isBlackout && (
        <div className="flex-shrink-0 mx-4 sm:mx-5 mt-3 rounded-2xl border border-white/10 bg-white/6 backdrop-blur-xl px-4 py-3 text-white/75">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/40">教师备注</span>
            <span className="text-[10px] text-white/30">仅教师可见</span>
          </div>
          <p className="text-xs mt-1 text-white/60">在编辑器中添加备注块后会在此显示。</p>
        </div>
      )}

      <div className="flex-1 flex relative mt-3 sm:mt-4 px-4 sm:px-5 pb-4 sm:pb-5">
        {project.mode === "longform" && sections.length > 0 && !isBlackout && (
          <aside className={`w-52 flex-shrink-0 mr-4 rounded-[24px] border border-white/10 bg-white/6 backdrop-blur-xl overflow-y-auto flex flex-col transition-opacity duration-300 ${hideUI ? "opacity-0 pointer-events-none" : ""}`}>
            <div className="p-4 border-b border-white/10">
              <span className="text-[10px] font-semibold text-white/40 uppercase tracking-[0.18em]">章节导航</span>
            </div>
            <div className="flex-1 py-2">
              {sections.map((name, i) => (
                <button
                  key={i}
                  onClick={() => scrollToSection(i)}
                  className={`block w-full text-left px-4 py-2.5 text-xs transition-colors border-l-2 ${
                    i === activeSection
                      ? "bg-white/8 text-white border-sage-300"
                      : "text-white/50 hover:text-white/85 hover:bg-white/6 border-transparent"
                  }`}
                >
                  {name}
                </button>
              ))}
            </div>
          </aside>
        )}

        <div className="flex-1 flex items-center justify-center relative rounded-[28px] overflow-hidden border border-white/8 bg-black/20 backdrop-blur-sm shadow-card">
          {isBlackout ? (
            <div className="absolute inset-0 bg-black flex items-center justify-center">
              <p className="text-white/35 text-sm">黑屏模式 · 按 B 恢复</p>
            </div>
          ) : renderedHtml ? (
            <iframe
              ref={iframeRef}
              srcDoc={renderedHtml}
              className="w-full h-full border-0 bg-white"
              style={{ maxWidth: 1280, margin: "0 auto" }}
              title="课堂展示"
              sandbox="allow-same-origin allow-scripts"
              onLoad={() => extractSections()}
            />
          ) : (
            <div className="text-center text-white/65 px-6">
              <div className="mx-auto w-20 h-20 rounded-full bg-white/6 flex items-center justify-center mb-4 border border-white/10">
                <svg className="w-8 h-8 text-white/30" fill="none" viewBox="0 0 24 24" strokeWidth={1.2} stroke="currentColor"><path d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"/><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
              </div>
              <h3 className="text-lg text-white/85 mb-2">课堂展示模式</h3>
              <p className="text-sm text-white/55 max-w-sm mx-auto">课件 HTML 将在此进入独立展示终态，工具栏只保留课堂控制所需能力。</p>
            </div>
          )}

          {timerRunning && !isBlackout && (
            <div className={`absolute top-5 right-5 rounded-2xl border border-white/10 bg-ink-900/88 backdrop-blur-xl px-4 py-3 flex items-center gap-3 ${hideUI ? "hidden" : ""}`}>
              <span className="text-2xl font-mono text-warning-400 font-bold tabular-nums">{formatTime(timerSeconds)}</span>
              <div className="flex flex-col gap-0.5">
                <button onClick={resetTimer} className="text-[10px] text-white/45 hover:text-white/75">重置</button>
                <button onClick={toggleTimer} className="text-[10px] text-white/45 hover:text-white/75">暂停</button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className={footerClasses}>
        <div className="flex items-center gap-3">
          <button onClick={() => setCurrentSlide((p) => Math.max(p - 1, 1))} className="text-white/55 hover:text-white disabled:opacity-30" disabled={currentSlide <= 1}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path d="M15 19l-7-7 7-7"/></svg>
          </button>
          <span className="text-xs text-white/55 font-mono tabular-nums">
            {currentSlide} / {totalSlides.current} 页
          </span>
          <button onClick={() => setCurrentSlide((p) => Math.min(p + 1, totalSlides.current))} className="text-white/55 hover:text-white disabled:opacity-30" disabled={currentSlide >= totalSlides.current}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path d="M9 5l7 7-7 7"/></svg>
          </button>
        </div>
        <span className="text-[10px] text-white/40">
          ←/→ 翻页 · Space 揭示 · T 计时 · B 黑屏 · F 全屏
        </span>
      </div>
    </div>
  );
}
