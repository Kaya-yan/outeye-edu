"use client";

import { JobStatus, STAGE_LABELS, ERROR_CODE_MESSAGES } from "@/lib/knowledge";

export default function DocumentProcessingStatus({ job }: { job: JobStatus }) {
  const isError = job.stage === "error";
  const isDone = job.stage === "done";

  const label =
    isError && job.error_code
      ? ERROR_CODE_MESSAGES[job.error_code] ?? job.error
      : STAGE_LABELS[job.stage];

  const progress =
    job.stage === "embedding" && job.progress?.total_chunks
      ? Math.round(
          (job.progress.processed_chunks / job.progress.total_chunks) * 100
        )
      : null;

  const color = isError
    ? "text-rose-600"
    : isDone
    ? "text-sage-700"
    : "text-ink-600";

  return (
    <div className="w-full">
      <div className={`flex items-center gap-2 text-sm ${color}`}>
        <span className="inline-block h-2 w-2 rounded-full bg-current" />
        <span>{label}</span>
        {progress !== null && (
          <span className="text-xs text-ink-400">
            ({job.progress!.processed_chunks}/{job.progress!.total_chunks})
          </span>
        )}
      </div>
      {job.stage === "embedding" && progress !== null && (
        <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-canvas-200">
          <div
            className="h-1.5 rounded-full bg-sage-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
