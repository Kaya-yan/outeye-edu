import type { ReactNode } from "react";

// 法律文档（用户协议/隐私政策）共用外壳：768px 栏宽 + 1.8 行高，正文可读性优先
export default function LegalDocShell({
  title,
  effectiveDate,
  children,
}: {
  title: string;
  effectiveDate: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-canvas-50 py-10 sm:py-14">
      <div className="mx-auto w-full max-w-[768px] px-4 sm:px-6">
        <header className="mb-6">
          <div className="section-title mb-2">OutEye Edu 1.0</div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-900">{title}</h1>
          <p className="mt-2 text-xs text-ink-400">生效日期：{effectiveDate}</p>
        </header>
        <div className="space-y-4">{children}</div>
        <p className="mt-6 text-center text-xs text-ink-400">
          如对本文件有疑问，请联系 <a className="legal-link" href="mailto:Kaya-yan@outlook.com">Kaya-yan@outlook.com</a>
        </p>
      </div>
    </div>
  );
}

export function LegalSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="data-card">
      <h2 className="text-base font-semibold text-ink-900">{title}</h2>
      <div className="mt-3 space-y-3 text-sm text-ink-700 leading-[1.8]">
        {children}
      </div>
    </section>
  );
}
