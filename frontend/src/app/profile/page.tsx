"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import { apiPost, apiPut, ApiError } from "@/lib/api";

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [oldPwd, setOldPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [pwdError, setPwdError] = useState("");
  const [pwdSuccess, setPwdSuccess] = useState("");
  const [changingPwd, setChangingPwd] = useState(false);

  if (!user) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-ink-500 mb-4">请先登录后查看个人中心。</p>
        <Link href="/login" className="btn-primary rounded-full px-5 py-2.5 inline-block">
          去登录
        </Link>
      </div>
    );
  }

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPwdError("");
    setPwdSuccess("");

    if (newPwd !== confirmPwd) {
      setPwdError("两次输入的新密码不一致");
      return;
    }
    if (newPwd.length < 8) {
      setPwdError("新密码长度至少 8 位");
      return;
    }
    if (newPwd === oldPwd) {
      setPwdError("新密码不能与原密码相同");
      return;
    }

    setChangingPwd(true);
    try {
      // 后端修改密码接口（假设为 PUT /users/me/password）
      // 若后端路径不同，请同步调整
      await apiPut("/users/me/password", {
        old_password: oldPwd,
        new_password: newPwd,
      });
      setPwdSuccess("密码修改成功，下次登录请使用新密码");
      setOldPwd("");
      setNewPwd("");
      setConfirmPwd("");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : "修改失败";
      setPwdError(msg);
    } finally {
      setChangingPwd(false);
    }
  };

  const sections = [
    { key: "account", label: "账号信息" },
    { key: "security", label: "安全" },
    { key: "preferences", label: "偏好设置" },
    { key: "content", label: "我的内容" },
    { key: "about", label: "关于" },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <header className="brand-surface px-6 py-8 sm:px-8 sm:py-10 mb-6 relative overflow-hidden">
        <div className="absolute right-[-6%] top-[-25%] h-56 w-56 rounded-full bg-primary-200/30 blur-3xl" />
        <div className="absolute left-[18%] bottom-[-30%] h-52 w-52 rounded-full bg-sage-200/25 blur-3xl" />

        <div className="relative flex items-center gap-5">
          <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-primary-200 to-sage-200 ring-1 ring-black/5 shadow-soft flex items-center justify-center text-ink-800 text-2xl font-semibold flex-shrink-0">
            {user.full_name?.charAt(0) || user.email.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="section-title mb-1">Personal Center</div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-ink-900">
              {user.full_name || user.email}
            </h1>
            <p className="mt-1 text-sm text-ink-500">{user.email}</p>
          </div>
        </div>
      </header>

      {/* 账号信息 */}
      <section id="account" className="page-surface-strong px-6 py-6 sm:px-8 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.678 0-5.243-.465-7.499-1.632z" />
          </svg>
          <h2 className="text-lg font-semibold text-ink-900">账号信息</h2>
        </div>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="data-card p-4">
            <dt className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-1">姓名</dt>
            <dd className="text-ink-900 font-medium">{user.full_name || "未设置"}</dd>
          </div>
          <div className="data-card p-4">
            <dt className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-1">邮箱</dt>
            <dd className="text-ink-900 font-medium break-all">{user.email}</dd>
          </div>
          <div className="data-card p-4">
            <dt className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-1">用户 ID</dt>
            <dd className="text-ink-900 font-mono text-xs break-all">{user.id || "（首次登录尚未拉取）"}</dd>
          </div>
          <div className="data-card p-4">
            <dt className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-1">角色</dt>
            <dd className="text-ink-900 font-medium">教师</dd>
          </div>
        </dl>
      </section>

      {/* 安全 */}
      <section id="security" className="page-surface-strong px-6 py-6 sm:px-8 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 3.75h10.5a2.25 2.25 0 002.25-2.25v-3.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v3.75a2.25 2.25 0 002.25 2.25z" />
          </svg>
          <h2 className="text-lg font-semibold text-ink-900">安全</h2>
        </div>

        <form onSubmit={handleChangePassword} className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl">
          <div>
            <label htmlFor="oldPwd" className="block text-sm font-medium text-ink-700 mb-1.5">当前密码</label>
            <input
              id="oldPwd"
              type="password"
              required
              value={oldPwd}
              onChange={(e) => setOldPwd(e.target.value)}
              className="morandi-input"
              placeholder="输入当前密码"
            />
          </div>
          <div>
            <label htmlFor="newPwd" className="block text-sm font-medium text-ink-700 mb-1.5">新密码</label>
            <input
              id="newPwd"
              type="password"
              required
              value={newPwd}
              onChange={(e) => setNewPwd(e.target.value)}
              className="morandi-input"
              placeholder="至少 8 位"
            />
          </div>
          <div>
            <label htmlFor="confirmPwd" className="block text-sm font-medium text-ink-700 mb-1.5">确认新密码</label>
            <input
              id="confirmPwd"
              type="password"
              required
              value={confirmPwd}
              onChange={(e) => setConfirmPwd(e.target.value)}
              className="morandi-input"
              placeholder="再次输入"
            />
          </div>

          <div className="sm:col-span-3 flex items-center gap-3">
            <button
              type="submit"
              disabled={changingPwd}
              className="btn-primary rounded-xl px-5 py-2.5 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {changingPwd ? "修改中..." : "修改密码"}
            </button>
            {pwdError && (
              <p className="text-sm text-rose-700">{pwdError}</p>
            )}
            {pwdSuccess && (
              <p className="text-sm text-sage-700">{pwdSuccess}</p>
            )}
          </div>
        </form>

        <div className="mt-4 pt-4 border-t border-black/5">
          <button
            onClick={logout}
            className="text-sm text-rose-700 hover:text-rose-900 transition-colors link-underline"
          >
            退出当前账户登录
          </button>
        </div>
      </section>

      {/* 偏好设置 */}
      <section id="preferences" className="page-surface-strong px-6 py-6 sm:px-8 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.594c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.43.992a7.723 7.723 0 010 .255c-.008.378.137.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.296 2.247a1.125 1.125 0 01-1.37.49l-1.217-.456c-.355-.133-.75-.072-1.075.124a6.47 6.47 0 01-.22.128c-.332.183-.582.495-.644.869l-.213 1.281c-.09.542-.56.94-1.11.94h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.47 6.47 0 01-.22-.127c-.325-.196-.72-.257-1.075-.124l-1.217.456a1.125 1.125 0 01-1.37-.49l-1.296-2.247a1.125 1.125 0 01.26-1.431l1.003-.827c.293-.24.438-.613.43-.992a7.723 7.723 0 010-.255c.008-.378-.137-.75-.43-.99l-1.005-.828a1.125 1.125 0 01-.26-1.43l1.296-2.247a1.125 1.125 0 011.37-.49l1.217.456c.355.133.75.072 1.075-.124.073-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.213-1.281z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <h2 className="text-lg font-semibold text-ink-900">偏好设置</h2>
        </div>

        <div className="data-card p-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-canvas-100 flex items-center justify-center text-ink-600">
              {theme === "light" ? (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.373-.386l1.591-1.591M3 12H5.25m.386-4.373l1.591 1.591M12 7.5a4.5 4.5 0 100 9 4.5 4.5 0 000-9z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
                </svg>
              )}
            </div>
            <div>
              <div className="text-sm font-medium text-ink-900">外观主题</div>
              <p className="text-xs text-ink-500 mt-0.5">
                切换白天或夜间主题，设置会自动保存。
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 rounded-full bg-canvas-100 p-1">
            <button
              onClick={() => setTheme("light")}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                theme === "light" ? "bg-white shadow-soft text-ink-900" : "text-ink-500 hover:text-ink-700"
              }`}
            >
              白天
            </button>
            <button
              onClick={() => setTheme("dark")}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                theme === "dark" ? "bg-white shadow-soft text-ink-900" : "text-ink-500 hover:text-ink-700"
              }`}
            >
              夜间
            </button>
          </div>
        </div>
      </section>

      {/* 我的内容 */}
      <section id="content" className="page-surface-strong px-6 py-6 sm:px-8 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
          </svg>
          <h2 className="text-lg font-semibold text-ink-900">我的内容</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link href="/history" className="archive-card p-5 hover-lift card-glow block">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-2">History</div>
            <div className="text-base font-semibold text-ink-900">历史记录</div>
            <p className="mt-1 text-xs text-ink-500">课文分析、教学方案与课件记录。</p>
          </Link>
          <Link href="/materials" className="archive-card p-5 hover-lift card-glow block">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-2">Materials</div>
            <div className="text-base font-semibold text-ink-900">我的资料</div>
            <p className="mt-1 text-xs text-ink-500">上传的教学大纲、词表与背景资料。</p>
          </Link>
          <Link href="/html-workbench" className="archive-card p-5 hover-lift card-glow block">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-2">Workbench</div>
            <div className="text-base font-semibold text-ink-900">HTML 工作台</div>
            <p className="mt-1 text-xs text-ink-500">上传 HTML 课件，可视化修改细节。</p>
          </Link>
        </div>
      </section>

      {/* 关于 */}
      <section id="about" className="page-surface-strong px-6 py-6 sm:px-8 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l1.5 1.5M15.75 15.75l1.5 1.5M11.25 15.75l1.5-1.5M15.75 11.25l1.5 1.5M3.75 12a8.25 8.25 0 1116.5 0 8.25 8.25 0 01-16.5 0z" />
          </svg>
          <h2 className="text-lg font-semibold text-ink-900">关于</h2>
        </div>

        <p className="text-sm leading-7 text-ink-700">
          OutEye Edu 是面向大学英语教师的 AI 备课助手，帮你把一篇课文变成一堂好课。
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="data-card p-4">
            <div className="text-sm font-semibold text-ink-900">课文分析</div>
            <p className="mt-1 text-xs leading-5 text-ink-500">词汇难度、句法与文化背景一目了然。</p>
          </div>
          <div className="data-card p-4">
            <div className="text-sm font-semibold text-ink-900">教案生成</div>
            <p className="mt-1 text-xs leading-5 text-ink-500">确认教学设置后，一键生成可编辑的教案。</p>
          </div>
          <div className="data-card p-4">
            <div className="text-sm font-semibold text-ink-900">课件制作</div>
            <p className="mt-1 text-xs leading-5 text-ink-500">教案直接生成网页课件，像改 PPT 一样精修。</p>
          </div>
        </div>

        <blockquote className="mt-4 border-l-2 border-primary-300 bg-canvas-100/60 px-4 py-3 text-sm leading-6 text-ink-600">
          教学设计以二语习得研究与欧洲语言共同参考框架（CEFR）为依据，结合教学理论库与百科知识检索生成，关键建议附来源可查。
        </blockquote>

        <p className="mt-3 text-xs text-ink-400">技术架构：Next.js 前端 + FastAPI 后端，内置大语言模型与知识检索。</p>

        <dl className="mt-5 space-y-3 border-t border-black/5 pt-4 text-sm">
          <div className="flex items-center justify-between py-2 border-b border-black/5">
            <dt className="text-ink-500">平台版本</dt>
            <dd className="text-ink-900 font-mono">OutEye Edu 1.0</dd>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-black/5">
            <dt className="text-ink-500">建设方</dt>
            <dd className="text-ink-900">挑战杯“揭榜挂帅”专项赛</dd>
          </div>
          <div className="flex items-center justify-between py-2">
            <dt className="text-ink-500">ICP 备案号</dt>
            <dd>
              <a
                href="https://beian.miit.gov.cn/"
                target="_blank"
                rel="noreferrer"
                className="text-primary-600 hover:text-primary-700 link-underline"
              >
                鲁ICP备2026044330号-1
              </a>
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
