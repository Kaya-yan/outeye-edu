"use client"

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

const navLinks = [
  { href: '/', label: '首页' },
  { href: '/projects', label: '项目管理' },
  { href: '/analysis', label: '智能分析' },
  { href: '/courseware', label: '教学课件' },
  { href: '/resources', label: '资源库' },
  { href: '/knowledge', label: '知识库' },
]

export default function Navbar() {
  const pathname = usePathname()
  const { user, isLoading, logout } = useAuth()

  if (pathname === '/login' || pathname === '/register') {
    return null
  }

  const userInitial = user?.full_name?.charAt(0) || user?.email?.charAt(0)?.toUpperCase() || '?'

  return (
    <>
      <div className="h-[2px] bg-gradient-to-r from-primary-300 via-sage-300 to-rose-300" />

      <nav className="sticky top-0 z-50 bg-white/72 backdrop-blur-xl border-b border-black/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-8">
              <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
                <div className="h-9 w-9 rounded-2xl bg-gradient-to-br from-primary-200 via-canvas-100 to-sage-200 ring-1 ring-black/5 shadow-soft flex items-center justify-center text-ink-700">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </div>
                <div className="leading-none">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Academic Desktop OS</div>
                  <div className="text-lg font-semibold tracking-tight text-ink-900">OutEye Edu</div>
                </div>
              </Link>

              <div className="hidden md:flex items-center gap-1 rounded-full bg-white/75 ring-1 ring-black/5 px-1.5 py-1 shadow-soft">
                {navLinks.map((link) => {
                  const isActive = pathname === link.href || (link.href !== '/' && pathname.startsWith(link.href))
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`relative inline-flex items-center rounded-full px-4 py-2 text-sm font-medium transition-all duration-200 ${
                        isActive
                          ? 'bg-canvas-500 text-ink-900 shadow-sm'
                          : 'text-ink-500 hover:text-ink-800 hover:bg-canvas-100'
                      }`}
                    >
                      {link.label}
                    </Link>
                  )
                })}
              </div>
            </div>

            <div className="hidden md:flex items-center gap-3 flex-shrink-0">
              {isLoading ? (
                <div className="h-9 w-24 rounded-full bg-canvas-200 animate-pulse" />
              ) : user ? (
                <>
                  <button className="relative h-10 w-10 rounded-full bg-white/80 ring-1 ring-black/5 text-ink-400 hover:text-ink-700 hover:bg-canvas-100 transition-colors">
                    <span className="sr-only">查看通知</span>
                    <svg className="w-5 h-5 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                    </svg>
                    <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-sage-500 ring-2 ring-white" />
                  </button>

                  <div className="relative group">
                    <button className="flex items-center gap-2 rounded-full bg-white/80 ring-1 ring-black/5 px-2 py-1.5 shadow-soft hover:bg-canvas-100 transition-colors">
                      <div className="h-9 w-9 rounded-full bg-gradient-to-br from-primary-200 to-sage-200 flex items-center justify-center text-ink-800 font-semibold text-sm">
                        {userInitial}
                      </div>
                      <div className="max-w-[140px] text-left">
                        <div className="text-xs text-ink-400">已登录</div>
                        <div className="text-sm font-medium text-ink-800 truncate">{user.full_name || user.email}</div>
                      </div>
                      <svg className="w-4 h-4 text-ink-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>

                    <div className="absolute right-0 top-full mt-2 w-56 rounded-2xl bg-white/95 backdrop-blur-md ring-1 ring-black/5 shadow-card py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
                      <div className="px-4 py-2 border-b border-black/5">
                        <p className="text-sm font-medium text-ink-900 truncate">{user.full_name || '用户'}</p>
                        <p className="text-xs text-ink-400 truncate">{user.email}</p>
                      </div>
                      <button
                        onClick={logout}
                        className="w-full text-left px-4 py-2.5 text-sm text-rose-700 hover:bg-rose-50 transition-colors"
                      >
                        退出登录
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <Link href="/login" className="btn-primary rounded-full px-5 py-2.5">
                  登录
                </Link>
              )}
            </div>

            <div className="md:hidden flex items-center gap-2">
              <Link href="/login" className="btn-secondary rounded-full px-4 py-2 text-xs">登录</Link>
              <button className="h-10 w-10 rounded-full bg-white/80 ring-1 ring-black/5 text-ink-500">
                <span className="sr-only">打开主菜单</span>
                <svg className="h-5 w-5 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </nav>
    </>
  )
}
