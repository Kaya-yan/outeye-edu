"use client";

import { useState } from "react";
import { apiPost } from "@/lib/api";

interface DifficultWord {
  word: string;
  level: string;
  count: number;
  in_awl: boolean;
}

interface WordDetail {
  phonetic: string;
  pos: string;
  gloss: string;
  teaching_example: string;
  board_note: string;
  original_sentence: string;
  source: "cached" | "llm" | "miss";
}

type DetailsMap = Record<string, WordDetail>;

const LEVEL_BADGES: Record<string, string> = {
  C1: "bg-rose-100 text-ink-900 border-rose-200",
  C2: "bg-rose-200 text-ink-900 border-rose-300",
  B2: "bg-accent-100 text-ink-900 border-accent-200",
  unknown: "bg-canvas-100 text-ink-600 border-black/10",
};

/**
 * 难词解析卡（任务F2）：难词统计区每词可点击展开
 * 音标 / 词性 / 语境释义 / 课文原句 / 教学例句 / 板书建议。
 * 详情由后端 word-detail-cache 缓存 + 轻量 LLM 补齐（同词不重复生成）；
 * 首次展开任一词时一次性拉全量，避免逐词请求。
 */
export default function DifficultWordsPanel({
  words,
  text,
  title,
  languageName,
  textLevel,
}: {
  words: DifficultWord[];
  text: string;
  title: string;
  languageName?: string;
  textLevel?: string;
}) {
  const [details, setDetails] = useState<DetailsMap | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");

  const loadDetails = async (): Promise<DetailsMap | null> => {
    if (details) return details;
    setLoading(true);
    setLoadError("");
    try {
      const resp = await apiPost<{ details: DetailsMap; meta: { fallback: boolean } }>(
        "/analysis/word-details",
        { words: words.map((w) => w.word), text }
      );
      setDetails(resp.details);
      return resp.details;
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "难词详情加载失败");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const toggleWord = async (word: string) => {
    if (expanded === word) {
      setExpanded(null);
      return;
    }
    setExpanded(word);
    if (!details && !loading) await loadDetails();
  };

  const handleExport = async () => {
    setExporting(true);
    setExportError("");
    try {
      const detailMap = (await loadDetails()) || {};
      const enriched = words.map((w) => ({
        ...w,
        ...detailMap[w.word],
      }));
      const token = localStorage.getItem("token");
      const resp = await fetch(`/api/v1/analysis/export`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          plan: {
            language_name: languageName,
            text_level: textLevel,
            words: enriched,
          },
          format: "vocab",
          title: `${title || "课文"} · 词汇讲义`,
        }),
      });
      if (!resp.ok) throw new Error(`导出失败（${resp.status}）`);
      const blob = await resp.blob();
      // 后端按 RFC 5987 双写文件名；优先取 filename* 的 UTF-8 真名
      const cd = resp.headers.get("Content-Disposition") || "";
      const starMatch = cd.match(/filename\*=UTF-8''([^;]+)/i);
      const downloadName = starMatch ? decodeURIComponent(starMatch[1]) : "词汇讲义.docx";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = downloadName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "导出失败，请稍后重试");
    } finally {
      setExporting(false);
    }
  };

  if (words.length === 0) return null;

  return (
    <div className="archive-surface p-5 sm:p-6">
      <div className="section-title mb-2">Vocabulary Cards</div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-ink-900">难词解析卡</h3>
          <p className="mt-1.5 text-sm text-ink-500 leading-6">
            点击任一难词展开教学卡片：音标、词性、语境释义、课文原句、教学例句与板书建议。
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting || loading}
          className="rounded-xl border border-primary-200 bg-primary-50 px-4 py-2 text-sm font-medium text-primary-700 transition-colors hover:bg-primary-100 disabled:opacity-50"
        >
          {exporting ? "讲义生成中…" : "导出词汇讲义"}
        </button>
      </div>

      {exportError && (
        <p className="mt-3 text-sm text-rose-600">{exportError}</p>
      )}
      {loadError && (
        <p className="mt-3 text-sm text-rose-600">{loadError}（可重试：再次点击词条）</p>
      )}
      {loading && (
        <p className="mt-3 text-sm text-ink-400">
          正在补齐教学详情（首次调用 AI 生成，同词下次直接命中缓存）…
        </p>
      )}

      <div className="mt-4 divide-y divide-black/5">
        {words.map((w) => {
          const d = details?.[w.word];
          const isOpen = expanded === w.word;
          return (
            <div key={w.word}>
              <button
                onClick={() => toggleWord(w.word)}
                aria-expanded={isOpen}
                className="flex w-full flex-wrap items-center gap-2 py-2.5 text-left transition-colors hover:bg-canvas-100/60 rounded-lg px-2 -mx-2"
              >
                <span className="text-sm font-semibold text-ink-900">{w.word}</span>
                <span className={`px-2 py-0.5 text-[11px] font-medium rounded-full border ${LEVEL_BADGES[w.level] || LEVEL_BADGES.unknown}`}>
                  {w.level === "unknown" ? "未定级" : w.level}
                </span>
                {w.in_awl && (
                  <span className="px-2 py-0.5 text-[11px] font-semibold rounded-full bg-primary-100 text-primary-700 border border-primary-200">
                    AWL
                  </span>
                )}
                {w.count > 1 && <span className="text-xs text-ink-400">出现 {w.count} 次</span>}
                <span className="ml-auto text-xs text-ink-300">{isOpen ? "收起 ▲" : "展开 ▼"}</span>
              </button>

              {isOpen && (
                <div className="mb-3 grid gap-3 rounded-2xl border border-black/5 bg-white p-4 md:grid-cols-2">
                  <Field label="音标" value={d?.phonetic} />
                  <Field label="词性" value={d?.pos} />
                  <Field label="语境释义" value={d?.gloss} />
                  <Field label="课文原句" value={d?.original_sentence} italic />
                  <Field label="教学例句" value={d?.teaching_example} span2 />
                  {d?.board_note && (
                    <div className="md:col-span-2">
                      <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">板书建议</div>
                      <pre className="mt-1.5 overflow-x-auto rounded-xl border border-black/10 bg-canvas-100 p-3 font-mono text-xs leading-6 text-ink-800">
{d.board_note}
                      </pre>
                    </div>
                  )}
                  {!d && loading && <p className="text-sm text-ink-400 md:col-span-2">详情加载中…</p>}
                  {!d && !loading && loadError && (
                    <p className="text-sm text-ink-400 md:col-span-2">暂无该词详情</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Field({ label, value, italic = false, span2 = false }: { label: string; value?: string; italic?: boolean; span2?: boolean }) {
  return (
    <div className={span2 ? "md:col-span-2" : ""}>
      <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">{label}</div>
      <p className={`mt-1 text-sm leading-6 text-ink-700 ${italic ? "italic" : ""}`}>
        {value || "—"}
      </p>
    </div>
  );
}
