"use client";

import { Evidence } from "@/lib/analysis";

function EvidenceRow({ e }: { e: Evidence }) {
  const isWiki = e.source_type === "wiki";
  return (
    <div className={`rounded-lg border p-3 ${isWiki ? "border-sage-200 bg-sage-50" : "border-accent-200 bg-accent-50"}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-ink-900">{e.title || "未命名"}</span>
        <span className="shrink-0 text-xs text-ink-400">
          相关性 {(e.relevance * 100).toFixed(0)}%
        </span>
      </div>
      {e.content && (
        <p className="mt-1.5 text-xs leading-relaxed text-ink-600">{e.content}</p>
      )}
    </div>
  );
}

export default function EvidenceDrawer({
  evidence,
}: {
  evidence: Evidence[];
}) {
  const wiki = evidence.filter((e) => e.source_type === "wiki");
  const rag = evidence.filter((e) => e.source_type === "rag");

  if (evidence.length === 0) {
    return (
      <p className="text-xs text-ink-400">无可用证据（该活动已降级）</p>
    );
  }

  return (
    <div className="space-y-3 border-t border-black/5 pt-3">
      {wiki.length > 0 && (
        <div>
          <div className="mb-1.5 text-xs font-semibold text-sage-700">理论依据</div>
          <div className="space-y-2">
            {wiki.map((e, i) => (
              <EvidenceRow key={`w-${i}`} e={e} />
            ))}
          </div>
        </div>
      )}
      {rag.length > 0 && (
        <div>
          <div className="mb-1.5 text-xs font-semibold text-accent-700">教师策略</div>
          <div className="space-y-2">
            {rag.map((e, i) => (
              <EvidenceRow key={`r-${i}`} e={e} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
