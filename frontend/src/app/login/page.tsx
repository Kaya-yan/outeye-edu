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
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-600 to-primary-800 flex items-center justify-center shadow-lg">
              <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </div>
            <span className="text-2xl font-bold gradient-text">OutEye Edu</span>
          </div>
          <h1 className="text-xl font-semibold text-navy-800">欢迎回来</h1>
          <p className="text-sm text-navy-500 mt-1">登录您的账户以继续</p>
          <blockquote className="mt-4 text-xs text-navy-400 italic border-l-2 border-primary-200 pl-3 max-w-xs mx-auto">
            "教育不是灌输，而是点燃火焰。" —— 苏格拉底
          </blockquote>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-2xl shadow-sm ring-1 ring-gray-900/5 p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-navy-700 mb-1.5">
                邮箱地址
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg bg-gray-50/50 text-navy-800 placeholder-navy-400 transition-all duration-200 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:bg-white outline-none"
                placeholder="your@email.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-navy-700 mb-1.5">
                密码
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg bg-gray-50/50 text-navy-800 placeholder-navy-400 transition-all duration-200 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:bg-white outline-none"
                placeholder="请输入密码"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-primary-600 to-primary-700 text-white py-2.5 px-5 rounded-lg font-medium shadow-sm hover:shadow-md hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  登录中...
                </span>
              ) : "登录"}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-navy-500">
            还没有账户？{" "}
            <Link href="/register" className="text-primary-600 hover:text-primary-700 font-medium">
              立即注册
            </Link>
          </div>
        </div>

        {/* Academic Disclaimer */}
        <div className="mt-6 text-center">
          <p className="text-[11px] text-navy-400/70 leading-relaxed max-w-sm mx-auto">
            本系统仅用于学术科研目的。所有分析数据将严格保密，不会用于任何商业用途。
            系统遵守相关法律法规，保护用户个人隐私与数据安全。
          </p>
        </div>
      </div>
    </div>
  );
}
