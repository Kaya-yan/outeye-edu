"use client";

import React, { useRef, useState } from "react";

type ImportMode = "upload" | "paste";

const IMPORT_KEY_PREFIX = "outeye:html-import:";

const SAMPLE_HTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>示例课件：The Gift of the Magi</title>
<style>
  body { font-family: "Microsoft YaHei", sans-serif; margin: 0; background: #f7f8fa; color: #1f2937; }
  .slide { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 16px; padding: 48px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
  h1 { font-size: 32px; margin: 0 0 8px; color: #2563eb; }
  .sub { color: #6b7280; margin-bottom: 24px; }
  .word { display: inline-block; background: #eff6ff; color: #1d4ed8; border-radius: 8px; padding: 4px 12px; margin: 4px; font-size: 14px; }
  p { line-height: 1.8; font-size: 16px; }
</style>
</head>
<body>
  <div class="slide">
    <h1>The Gift of the Magi</h1>
    <div class="sub">欧·亨利 · 阅读课 · 90 分钟</div>
    <p>This story is about a young couple who sacrifice their most prized possessions to buy each other Christmas gifts.</p>
    <div>
      <span class="word">sacrifice</span>
      <span class="word">possession</span>
      <span class="word">prized</span>
    </div>
  </div>
</body>
</html>`;

export default function HtmlWorkbenchPage() {
  const [mode, setMode] = useState<ImportMode>("upload");
  const [html, setHtml] = useState("");
  const [title, setTitle] = useState("");
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [dragOver, setDragOver] = useState(false);

  const loadFile = (file: File) => {
    setError("");
    if (!/\.(html?|txt)$/i.test(file.name)) {
      setError("请选择 HTML 文件（.html 或 .htm）");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setHtml(String(reader.result || ""));
      setFileName(file.name);
      setTitle(file.name.replace(/\.(html?|txt)$/i, ""));
    };
    reader.onerror = () => setError("读取文件失败，请重试");
    reader.readAsText(file);
  };

  const loadSample = () => {
    setError("");
    setMode("paste");
    setHtml(SAMPLE_HTML);
    setTitle("示例课件：The Gift of the Magi");
    setFileName("示例课件.html");
  };

  const startEdit = () => {
    const content = html.trim();
    if (content.length < 50 || !content.includes("<")) {
      setError("请先上传文件或粘贴 HTML 代码");
      return;
    }
    const key = IMPORT_KEY_PREFIX + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    try {
      sessionStorage.setItem(key, JSON.stringify({ html: content, title: title.trim() || "未命名课件", mode: "slides" }));
    } catch {
      setError("内容过大，请精简后重试");
      return;
    }
    window.location.href = `/editor/index.html#import=${encodeURIComponent(key)}`;
  };

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <header className="mx-auto mb-6 max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900 sm:text-3xl">HTML 工作台</h1>
        <p className="mt-2 text-sm text-ink-500">上传 HTML 课件，像改 PPT 一样修改每一个细节。</p>
      </header>

      <main className="mx-auto max-w-3xl space-y-4">
        <div className="inline-flex rounded-2xl border border-black/5 bg-white p-1 shadow-soft">
          <button
            onClick={() => setMode("upload")}
            className={`rounded-xl px-5 py-2 text-sm font-medium transition-colors ${
              mode === "upload" ? "bg-primary-600 text-white" : "text-ink-500 hover:bg-canvas-100"
            }`}
          >
            上传文件
          </button>
          <button
            onClick={() => setMode("paste")}
            className={`rounded-xl px-5 py-2 text-sm font-medium transition-colors ${
              mode === "paste" ? "bg-primary-600 text-white" : "text-ink-500 hover:bg-canvas-100"
            }`}
          >
            粘贴代码
          </button>
        </div>

        {mode === "upload" ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const file = e.dataTransfer.files?.[0];
              if (file) loadFile(file);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-colors ${
              dragOver ? "border-primary-400 bg-primary-50" : "border-black/10 bg-white hover:border-primary-300 hover:bg-canvas-50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".html,.htm,text/html"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) loadFile(file);
              }}
            />
            <svg className="mx-auto h-10 w-10 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
            </svg>
            <p className="mt-4 text-sm font-medium text-ink-800">点击选择，或把 HTML 文件拖到这里</p>
            <p className="mt-1 text-xs text-ink-400">支持 .html / .htm 文件</p>
            {fileName && <p className="mt-3 text-sm text-primary-700">已选择：{fileName}</p>}
          </div>
        ) : (
          <div>
            <textarea
              value={html}
              onChange={(e) => setHtml(e.target.value)}
              placeholder="<html>…把 HTML 代码粘贴到这里…</html>"
              spellCheck={false}
              className="morandi-input font-mono h-64 resize-y text-xs leading-5"
            />
            <p className="mt-2 text-xs text-ink-400">粘贴完整 HTML 代码（含 &lt;style&gt; 样式效果最佳）</p>
          </div>
        )}

        <div className="flex items-center justify-between gap-4">
          <button onClick={loadSample} className="text-sm text-primary-600 hover:text-primary-700 link-underline">
            没有文件？加载示例试试
          </button>
          <button onClick={startEdit} className="btn-primary px-6 py-3 text-base">
            开始编辑
          </button>
        </div>

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 p-4">
            <div className="min-h-[1.5rem] w-1 flex-shrink-0 rounded-full bg-red-400" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="data-card mt-2 p-5">
          <div className="text-sm font-semibold text-ink-900">先看效果，再修改</div>
          <p className="mt-2 text-sm leading-6 text-ink-500">
            进入编辑器后，建议先用顶部的「预览」按钮查看课件整体效果，再动手修改细节。
          </p>
        </div>
      </main>
    </div>
  );
}
