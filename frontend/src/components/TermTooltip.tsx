"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { glossary, GlossaryEntry } from "@/lib/glossary";

interface TermTooltipProps {
  term: string;
  children?: ReactNode;
  /** 显示位置：默认上方 */
  side?: "top" | "bottom";
  /** 整行触发：外层占满父容器宽度，用于卡片标签行等小字号场景 */
  block?: boolean;
  /** 后端术语表条目（含按本文数值实例化的解读）；缺省回退本地字典 */
  entry?: GlossaryEntry;
  /** 点击请求完整解读抽屉；缺省回退 TermDetailContext（由白盒结果页统一提供） */
  onOpenFull?: (term: string, entry: GlossaryEntry) => void;
}

/**
 * 宿主组件把「打开完整解读抽屉」的回调放进 Context，
 * 卡片内部的大量 TermTooltip 调用点无需逐个透传。
 */
export const TermDetailContext = createContext<((term: string, entry: GlossaryEntry) => void) | null>(null);

const BUBBLE_W = 288; // w-72
const GAP = 8;

/**
 * 术语 Tooltip：hover / focus / 点按 触发；再点或点「查看完整解读」打开抽屉。
 *
 * 气泡经 portal 渲染到 document.body 并用 fixed 定位——卡片容器的
 * overflow:hidden 与内部 z-index 层级都不再影响可见性（G2 回归根因）。
 * 交互：桌面 hover 出气泡、点击进抽屉；触屏无 hover，首点点按出气泡，
 * 气泡内按钮或再次点按进抽屉；Esc / 点外部 / 移出关闭。
 */
export default function TermTooltip({ term, children, side = "top", block = false, entry: entryOverride, onOpenFull }: TermTooltipProps) {
  const entry = entryOverride || glossary[term];
  // useContext 必须无条件调用：`a || useContext(...)` 短路会跳过 hook，违反 rules-of-hooks
  const contextOpen = useContext(TermDetailContext);
  const openFull = onOpenFull || contextOpen;
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const triggerRef = useRef<HTMLSpanElement>(null);
  const bubbleRef = useRef<HTMLDivElement>(null);

  const [mounted, setMounted] = useState(false);
  const [canHover, setCanHover] = useState(true);

  useEffect(() => {
    setMounted(true);
    // 触屏点按后浏览器补发的兼容事件会伪装成 mouse pointerenter，
    // 若据此开气泡，click 会判定「已打开」直接进抽屉——按设备能力门控：
    // 无 hover 能力的设备上气泡只由点按驱动，首点出气泡、再点进抽屉
    setCanHover(window.matchMedia("(hover: hover)").matches);
  }, []);

  // 入场动画 uiFadeUp 首帧自带 translateY(18px)，高气泡动画期间会短暂
  // 压住触发器，把指针「挤」进气泡触发 pointerout——若立即关闭会陷入
  // 开-关振荡。关闭一律延迟 120ms，指针移入气泡即取消（经典 tooltip 宽限）
  const closeTimerRef = useRef<number | null>(null);
  const cancelClose = useCallback(() => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);
  const scheduleClose = useCallback(() => {
    cancelClose();
    closeTimerRef.current = window.setTimeout(() => {
      closeTimerRef.current = null;
      setOpen(false);
    }, 120);
  }, [cancelClose]);
  useEffect(() => cancelClose, [cancelClose]);

  const place = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const vw = window.innerWidth || 1200;
    const vh = window.innerHeight || 800;
    // 气泡渲染后才能实测高度；首拍先用估值，rAF 后再校一次。
    // 定位直接算绝对 left/top（不用 transform）：入场动画的关键帧会
    // 覆盖 inline transform，导致首帧位置漂移
    const h = bubbleRef.current?.offsetHeight || 160;
    const left = Math.min(Math.max(r.left + r.width / 2 - BUBBLE_W / 2, 8), Math.max(8, vw - BUBBLE_W - 8));
    if (side !== "bottom" && r.top - GAP >= h + 8) {
      setPos({ left, top: r.top - GAP - h });
    } else if (r.bottom + GAP + h <= vh - 8) {
      setPos({ left, top: r.bottom + GAP });
    } else {
      setPos({ left, top: Math.max(Math.min(r.bottom + GAP, vh - h - 8), 8) });
    }
  }, [side]);

  useLayoutEffect(() => {
    if (!open) return;
    place();
    const raf = requestAnimationFrame(place); // 气泡挂载后用实测高度复核
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", place, true);
      window.removeEventListener("resize", place);
    };
  }, [open, place]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        cancelClose();
        setOpen(false);
      }
    };
    const onPointer = (e: PointerEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t) || bubbleRef.current?.contains(t)) return;
      cancelClose();
      setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointer);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointer);
    };
  }, [open, cancelClose]);

  if (!entry) {
    return <>{children || term}</>;
  }

  const openDetail = () => {
    cancelClose();
    setOpen(false);
    openFull?.(term, entry);
  };

  return (
    <span className={`relative items-center align-baseline ${block ? "flex w-full" : "inline-flex"}`}>
      <span
        ref={triggerRef}
        tabIndex={0}
        role="button"
        aria-expanded={open}
        onPointerEnter={(e) => {
          if (!canHover || e.pointerType === "touch") return;
          cancelClose();
          setOpen(true);
        }}
        onPointerLeave={(e) => {
          if (!canHover || e.pointerType === "touch") return;
          scheduleClose();
        }}
        onFocus={() => {
          // 触屏点按的 focus 先于 click 到达，若在此开气泡会被 click 判定
          // 「已打开」直接进抽屉；无 hover 设备改由 Enter 键出气泡
          if (canHover) setOpen(true);
        }}
        onBlur={scheduleClose}
        onClick={() => (open ? openDetail() : setOpen(true))}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            open ? openDetail() : setOpen(true);
          }
        }}
        className="cursor-help underline decoration-dotted decoration-ink-300 underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-primary-300 rounded"
      >
        {children || term}
      </span>
      <svg
        className="w-3 h-3 ml-0.5 text-ink-400 inline-block flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l1.5 1.5m0 0l1.5 1.5m-1.5-1.5l-1.5 1.5m1.5-1.5l1.5-1.5" />
      </svg>

      {mounted &&
        open &&
        pos &&
        createPortal(
          <div
            ref={bubbleRef}
            role="tooltip"
            data-term-tooltip={term}
            onPointerEnter={cancelClose}
            onPointerLeave={scheduleClose}
            style={{ position: "fixed", left: pos.left, top: pos.top, width: BUBBLE_W }}
            className="z-[95] max-w-[86vw] p-3 rounded-xl dropdown-surface text-left animate-[uiFadeUp_0.15s_ease-out]"
          >
            <div className="text-xs font-semibold text-ink-900 mb-1">{entry.name || term}</div>
            <div className="text-xs text-ink-700 leading-relaxed">{entry.definition}</div>
            {entry.interpretation && (
              <div className="mt-1.5 text-[11px] text-ink-500 leading-relaxed">
                <span className="font-semibold text-ink-600">解读：</span>
                {entry.interpretation}
              </div>
            )}
            {entry.teaching && (
              <div className="mt-1 text-[11px] text-ink-500 leading-relaxed">
                <span className="font-semibold text-ink-600">教学：</span>
                {entry.teaching}
              </div>
            )}
            {openFull && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  openDetail();
                }}
                className="mt-2 block w-full rounded-lg border border-primary-200 bg-primary-50 px-2 py-1 text-[11px] font-medium text-primary-700 transition-colors hover:bg-primary-100"
              >
                点击查看完整解读 →
              </button>
            )}
          </div>,
          document.body
        )}
    </span>
  );
}
