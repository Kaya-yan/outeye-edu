"use client"

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

const navLinks = [
  { href: '/', label: '首页' },
  { href: '/projects', label: '项目管理' },
  { href: '/analysis', label: '智能分析' },
  { href: '/resources', label: '资源库' },
  { href: '/knowledge', label: '知识库' },
]

export default function Navbar() {
  const pathname = usePathname()
  const { user, isLoading, logout } = useAuth()

  // Don't show navbar on login/register pages
  if (pathname === '/login' || pathname === '/register') {
    return null
  }

  const userInitial = user?.full_name?.charAt(0) || user?.email?.charAt(0)?.toUpperCase() || '?'

  return (
    <>
      {/* Top gradient accent line */}
      <div className="h-[3px] bg-gradient-to-r from-primary-400 via-primary-600 to-primary-800" />

      {/* Navigation bar */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            {/* Logo & Links */}
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center gap-2">
                <svg className="w-7 h-7 text-primary-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <Link href="/" className="flex items-baseline gap-1">
                  <span className="text-xl font-bold text-gray-900 tracking-tight">OutEye</span>
                  <span className="text-xl font-light text-primary-600">Edu</span>
                </Link>
              </div>

              <div className="hidden sm:ml-8 sm:flex sm:space-x-1">
                {navLinks.map((link) => {
                  const isActive = pathname === link.href
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`relative inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                        isActive
                          ? 'text-primary-600 font-semibold'
                          : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
                      }`}
                    >
                      {link.label}
                      {isActive && (
                        <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-[2px] bg-primary-500 rounded-full" />
                      )}
                    </Link>
                  )
                })}
              </div>
            </div>

            {/* Right side */}
            <div className="hidden sm:flex sm:items-center sm:gap-3">
              {isLoading ? (
                <div className="h-9 w-9 rounded-full bg-gray-100 animate-pulse" />
              ) : user ? (
                <>
                  {/* Notification bell */}
                  <button className="relative p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20">
                    <span className="sr-only">查看通知</span>
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                    </svg>
                    <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary-500 ring-2 ring-white" />
                  </button>

                  {/* User menu */}
                  <div className="relative group">
                    <button className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-gray-50 transition-colors">
                      <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center ring-2 ring-transparent group-hover:ring-primary-300 transition-all duration-200">
                        <span className="text-primary-700 font-semibold text-sm">{userInitial}</span>
                      </div>
                      <span className="text-sm text-navy-700 font-medium max-w-[100px] truncate">
                        {user.full_name || user.email}
                      </span>
                      <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>

                    {/* Dropdown */}
                    <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-xl shadow-elevated ring-1 ring-gray-900/5 py-1.5 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                      <div className="px-4 py-2 border-b border-gray-100">
                        <p className="text-sm font-medium text-navy-800 truncate">{user.full_name || '用户'}</p>
                        <p className="text-xs text-navy-500 truncate">{user.email}</p>
                      </div>
                      <button
                        onClick={logout}
                        className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
                        </svg>
                        退出登录
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <Link
                  href="/login"
                  className="bg-gradient-to-r from-primary-600 to-primary-700 text-white py-2 px-4 rounded-lg text-sm font-medium shadow-sm hover:shadow-md hover:scale-[1.02] transition-all duration-200"
                >
                  登录
                </Link>
              )}
            </div>

            {/* Mobile menu button */}
            <div className="flex items-center sm:hidden">
              <button className="inline-flex items-center justify-center p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500/20">
                <span className="sr-only">打开主菜单</span>
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
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
