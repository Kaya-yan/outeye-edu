// CEFR 显示层中文标签（内部仍存 A1-C2 代码）
export const CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"] as const;

export const CEFR_LABELS: Record<string, string> = {
  A1: "入门（小学）",
  A2: "初级（初中）",
  B1: "中级（高中）",
  B2: "中高级（四级）",
  C1: "高级（六级·考研）",
  C2: "精通（专八）",
};

export function cefrLabel(code: string): string {
  return CEFR_LABELS[code] || code;
}

export function cefrShortLabel(code: string): string {
  const label = CEFR_LABELS[code];
  if (!label) return code;
  return `${code} · ${label.replace(/（.*）/, "")}`;
}
