"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "登录失败，请检查邮箱和密码");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen desk-wash px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl items-center justify-center">
        <div className="grid w-full overflow-hidden rounded-[28px] border border-black/5 bg-white/80 shadow-elevated backdrop-blur-sm lg:grid-cols-[1.08fr_0.92fr]">
          {/* Welcome panel */}
          <div className="relative overflow-hidden bg-gradient-to-br from-ink-900 via-ink-800 to-archive-900 px-8 py-10 text-white lg:px-12 lg:py-14">
            <div className="absolute -right-16 -top-12 h-52 w-52 rounded-full bg-primary-200/10 blur-3xl" />
            <div className="absolute -left-12 bottom-0 h-48 w-48 rounded-full bg-rose-200/10 blur-3xl" />

            <div className="relative flex h-full flex-col justify-between gap-8">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-[11px] font-medium tracking-[0.18em] uppercase text-white/75">
                  Academic Desktop OS
                </div>
                <h1 className="mt-8 text-4xl font-semibold tracking-tight text-white lg:text-5xl">欢迎回来</h1>
                <p className="mt-4 max-w-md text-sm leading-7 text-white/70 lg:text-base">
                  登录你的 OutEye Edu 工作台，继续完成课文分析、教学设计、资源整理与 HTML 课件创作。
                </p>
              </div>

              <div className="space-y-5">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                  <p className="text-xs uppercase tracking-[0.18em] text-white/45">Today’s flow</p>
                  <div className="mt-4 flex flex-col gap-3 text-sm text-white/75">
                    <div className="flex items-center gap-3"><span className="h-2 w-2 rounded-full bg-sage-300" /> 课文智能分析</div>
                    <div className="flex items-center gap-3"><span className="h-2 w-2 rounded-full bg-primary-200" /> 双源检索与教案生成</div>
                    <div className="flex items-center gap-3"><span className="h-2 w-2 rounded-full bg-rose-200" /> 教学 HTML 课件工作台</div>
                  </div>
                </div>

                <Link
                  href="/register"
                  className="inline-flex items-center justify-center rounded-full border border-white/25 px-6 py-3 text-sm font-semibold text-white hover:bg-white/10 transition-colors"
                >
                  创建新账户
                </Link>
              </div>
            </div>
          </div>

          {/* Form panel */}
          <div className="bg-white/85 px-6 py-10 sm:px-8 lg:px-10 lg:py-14">
            <div className="mx-auto max-w-md">
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-4">
                  <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-primary-200 via-canvas-100 to-sage-200 ring-1 ring-black/5 shadow-soft flex items-center justify-center text-ink-700">
                    <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </div>
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">OutEye Edu</div>
                    <div className="text-xl font-semibold text-ink-900">登录账户</div>
                  </div>
                </div>
                <p className="text-sm leading-6 text-ink-500">
                  用更柔和、更专注的工作流，回到你的学术桌面继续创作。
                </p>
              </div>

              <div className="page-surface-strong p-6 sm:p-7">
                <form onSubmit={handleSubmit} className="space-y-5">
                  {error && (
                    <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                      {error}
                    </div>
                  )}

                  <div>
                    <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-ink-700">
                      邮箱地址
                    </label>
                    <input
                      id="email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="morandi-input"
                      placeholder="your@email.com"
                    />
                  </div>

                  <div>
                    <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-ink-700">
                      密码
                    </label>
                    <input
                      id="password"
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="morandi-input"
                      placeholder="请输入密码"
                    />
                  </div>

                  <button type="submit" disabled={loading} className="btn-primary w-full rounded-xl py-3 disabled:opacity-60 disabled:cursor-not-allowed">
                    {loading ? (
                      <span className="inline-flex items-center gap-2">
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        登录中...
                      </span>
                    ) : (
                      "登录"
                    )}
                  </button>
                </form>
              </div>

              <div className="mt-6 text-center text-sm text-ink-500">
                还没有账户？{' '}
                <Link href="/register" className="font-medium text-ink-900 hover:text-ink-700 underline underline-offset-4 decoration-primary-300">
                  立即注册
                </Link>
              </div>

              <p className="mt-6 text-center text-[11px] leading-6 text-ink-400 max-w-sm mx-auto">
                本系统仅用于学术与教学研究场景。我们会以最小必要原则处理你的内容与项目数据。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
