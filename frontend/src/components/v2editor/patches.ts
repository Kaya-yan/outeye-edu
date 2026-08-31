import type { VeTarget } from "./rpc";

export const EXPORT_STYLE_ID = "ve-export-patches";

export type VePatchKind = "css" | "text" | "image" | "insert";

export type VeInsertPosition = "after" | "before" | "append";

export interface VePatchFingerprint {
  tag: string;
  childCount: number;
  text: string;
  w: number;
  h: number;
}

export interface VePatch {
  id: string;
  kind: VePatchKind;
  selector: string;
  label: string;
  prop?: string;
  value?: string;
  newText?: string;
  newSrc?: string;
  position?: VeInsertPosition;
  html?: string;
  oeId?: string;
  fingerprint: VePatchFingerprint;
}

export function normalizePatch(p: VePatch): VePatch {
  return { ...p, kind: p.kind || "css" };
}

export function makeFingerprint(target: VeTarget): VePatchFingerprint {
  return {
    tag: target.tag,
    childCount: target.childCount,
    text: (target.text || "").slice(0, 40),
    w: Math.round(target.rect.w),
    h: Math.round(target.rect.h),
  };
}

export function patchId(selector: string, kind: VePatchKind, prop?: string): string {
  return kind === "css" ? `${selector}||${prop}` : `${selector}||${kind}`;
}

export function insertPatchId(selector: string, seq: number): string {
  return `${selector}||insert||${seq}`;
}

// 取该锚点上已有 insert 序号的最大值 +1：移除某条后再插入不会撞出重复 patch id
export function nextInsertSeq(patches: VePatch[], selector: string): number {
  let max = 0;
  for (const p of patches) {
    if (p.kind === "insert" && p.selector === selector) {
      const m = p.id.match(/insert\|\|(\d+)$/);
      if (m) max = Math.max(max, parseInt(m[1], 10));
    }
  }
  return max + 1;
}

// 插入元素用 data-oe-id 作稳定锚点，避开 nth-of-type 在插入位移后失效
export function nextOeId(patches: VePatch[], prefix: string): string {
  const used = new Set(
    patches.filter((p) => p.kind === "insert" && p.oeId).map((p) => p.oeId as string)
  );
  let n = 1;
  while (used.has(`${prefix}${n}`)) n++;
  return `${prefix}${n}`;
}

export function insertWrapperSelector(patchIdStr: string): string {
  return `[data-ve-insert="${patchIdStr}"]`;
}

export function targetLabel(target: VeTarget): string {
  return target.component ? `${target.tag} · ${target.component}` : target.tag;
}

export function cssPatches(patches: VePatch[]): VePatch[] {
  return patches.filter((p) => (p.kind || "css") === "css" && p.prop);
}

export function hasDomPatches(patches: VePatch[]): boolean {
  return patches.some((p) => p.kind === "text" || p.kind === "image" || p.kind === "insert");
}

export function buildPatchCss(patches: VePatch[]): string {
  const list = cssPatches(patches);
  if (list.length === 0) return "";
  const declsBySelector: { [selector: string]: string[] } = {};
  const order: string[] = [];
  for (const p of list) {
    if (!declsBySelector[p.selector]) {
      declsBySelector[p.selector] = [];
      order.push(p.selector);
    }
    declsBySelector[p.selector].push(`  ${p.prop}: ${p.value} !important;`);
  }
  const rules: string[] = [];
  for (const sel of order) {
    rules.push(`${sel} {\n${declsBySelector[sel].join("\n")}\n}`);
  }
  return rules.join("\n\n");
}

export function injectExportStyle(html: string, css: string): string {
  const tag = `<style id="${EXPORT_STYLE_ID}">\n${css}\n</style>`;
  if (/<\/head>/i.test(html)) return html.replace(/<\/head>/i, `${tag}\n</head>`);
  if (/<\/body>/i.test(html)) return html.replace(/<\/body>/i, `${tag}\n</body>`);
  return html + tag;
}

export function stripExportStyle(html: string): string {
  return html.replace(
    new RegExp(`<style id="${EXPORT_STYLE_ID}"[^>]*>[\\s\\S]*?</style>\\s*`, "i"),
    ""
  );
}

export function exportFileName(title: string): string {
  const safe = (title || "courseware").replace(/[\\/:*?"<>|\s]+/g, "-").slice(0, 60);
  return `${safe}-v2.html`;
}
