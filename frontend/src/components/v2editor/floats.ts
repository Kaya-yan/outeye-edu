/**
 * 浮动层（任务G4）：文本框/图片/便签按百分比坐标自由摆放在节内。
 * 纯函数模块：宿主建补丁、agent 物化、导出与单测共用同一份 HTML 契约。
 *
 * - 坐标为元素左上角相对所属节（.oe-section / section.page）内容盒的百分比
 * - 宽度按节宽百分比，高度随内容自适应；渲染期 agent 用实测高度复核下边界
 * - 便签（note）仅编辑器内使用，导出时剔除
 */

export type VeFloatKind = "textbox" | "image" | "note";

export interface VeFloatItem {
  id: string;
  kind: VeFloatKind;
  /** 1-based 节号（data-sec / data-page） */
  section: number;
  xPct: number;
  yPct: number;
  wPct: number;
  /** textbox/note：纯文本；image：src（URL 或 data:） */
  content: string;
}

/** 高于正文、低于编辑器工具栏与 ve-ui 层 */
export const FLOAT_Z = 30;

export const FLOAT_DEFAULT_W_PCT: Record<VeFloatKind, number> = {
  textbox: 32,
  image: 34,
  note: 22,
};

export const FLOAT_KIND_NAME: Record<VeFloatKind, string> = {
  textbox: "文本框",
  image: "图片",
  note: "便签",
};

export const FLOAT_DEFAULT_CONTENT: Record<VeFloatKind, string> = {
  textbox: "双击编辑这段文字",
  image: "",
  note: "便签：双击编辑",
};

export function nextFloatId(used: Iterable<string>): string {
  const set = new Set(used);
  let n = 1;
  while (set.has(`oe-fl${n}`)) n++;
  return `oe-fl${n}`;
}

export function clampW(wPct: number): number {
  return Math.min(Math.max(wPct, 4), 100);
}

export function clampX(xPct: number, wPct: number): number {
  const w = clampW(wPct);
  return Math.min(Math.max(xPct, 0), 100 - w);
}

export function clampY(yPct: number): number {
  return Math.min(Math.max(yPct, 0), 100);
}

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function unescapeHtml(s: string): string {
  return s
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function fmtPct(n: number): string {
  return String(Math.round(n * 100) / 100);
}

const SHELL_STYLE: Record<VeFloatKind, string> = {
  textbox: "background:#fff;border:1px solid #d6d2c7;border-radius:10px;padding:12px 16px;box-shadow:0 2px 8px rgba(0,0,0,.08)",
  note: "background:#fdf3b8;border:1px solid #e8d778;border-radius:4px 12px 4px 4px;padding:10px 12px;box-shadow:0 2px 6px rgba(0,0,0,.12)",
  image: "background:#fff;border-radius:8px;overflow:visible",
};

/** 浮层 HTML：agent 物化与导出共用的唯一产物，导出时原样保留（note 除外） */
export function buildFloatHtml(f: VeFloatItem): string {
  const x = fmtPct(clampX(f.xPct, f.wPct));
  const y = fmtPct(clampY(f.yPct));
  const w = fmtPct(clampW(f.wPct));
  const pos = `position:absolute;left:${x}%;top:${y}%;width:${w}%`;
  let inner: string;
  if (f.kind === "image") {
    inner = `<img src="${escapeHtml(f.content)}" alt="浮动图片" style="display:block;width:100%;height:auto;border-radius:8px">`;
  } else {
    const text = f.kind === "note"
      ? "font:14px/1.6 system-ui,sans-serif;color:#5b4a12"
      : "font:16px/1.7 system-ui,sans-serif;color:#2b2b33";
    inner = `<div class="ve-fl-text" style="${text};white-space:pre-wrap">${escapeHtml(f.content)}</div>`;
  }
  return (
    `<div data-float="1" data-oe-float="${f.id}" data-float-kind="${f.kind}"` +
    ` style="box-sizing:border-box;z-index:${FLOAT_Z};${pos};${SHELL_STYLE[f.kind]}">${inner}</div>`
  );
}

/**
 * 从 HTML 解析回浮层（导出往返契约校验用）。
 * 仅需识别 buildFloatHtml 的受控产物：属性齐全、内容为转义纯文本/受控 img。
 * HTML 不承载节号（节=DOM 位置），解析结果 section 恒为 0。
 */
export function parseFloatsFromHtml(html: string): VeFloatItem[] {
  const out: VeFloatItem[] = [];
  const tagRe = /<div\s[^>]*data-float="1"[^>]*>/g;
  let m: RegExpExecArray | null;
  while ((m = tagRe.exec(html)) !== null) {
    const tag = m[0];
    const id = /data-oe-float="([^"]*)"/.exec(tag)?.[1];
    const kind = /data-float-kind="(textbox|image|note)"/.exec(tag)?.[1] as VeFloatKind | undefined;
    if (!id || !kind) continue;
    const style = /style="([^"]*)"/.exec(tag)?.[1] || "";
    const pct = (prop: string) => {
      const v = new RegExp(prop + ":([\\d.]+)%").exec(style)?.[1];
      return v ? parseFloat(v) : 0;
    };
    let content = "";
    if (kind === "image") {
      content = unescapeHtml(/<img src="([^"]*)"/.exec(html.slice(m.index))?.[1] || "");
    } else {
      const seg = html.slice(m.index);
      const tm = /<div class="ve-fl-text"[^>]*>([\s\S]*?)<\/div><\/div>/.exec(seg);
      content = tm ? unescapeHtml(tm[1]) : "";
    }
    out.push({
      id,
      kind,
      section: 0,
      xPct: pct("left"),
      yPct: pct("top"),
      wPct: pct("width"),
      content,
    });
  }
  return out;
}
