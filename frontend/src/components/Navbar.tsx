"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";

const navLinks = [
  { href: "/", label: "首页" },
  { href: "/projects", label: "项目管理" },
  { href: "/analysis", label: "智能分析" },
  { href: "/courseware", label: "教学课件" },
  { href: "/resources", label: "资源库" },
  { href: "/knowledge", label: "知识库" },
];

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭下拉
  useEffect(() => {
    if (!menuOpen) return;
    const onDocClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [menuOpen]);

  // 路由切换时关闭菜单
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  if (pathname === "/login" || pathname === "/register") {
    return null;
  }

  const userInitial = user?.full_name?.charAt(0) || user?.email?.charAt(0)?.toUpperCase() || "?";

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
  };

  const UserMenu = () => (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setMenuOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full bg-white/80 ring-1 ring-black/5 px-2 py-1.5 shadow-soft hover:bg-canvas-100 transition-colors"
        aria-expanded={menuOpen}
        aria-haspopup="menu"
      >
        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary-200 to-sage-200 flex items-center justify-center text-ink-800 font-semibold text-sm flex-shrink-0">
          {userInitial}
        </div>
        <div className="hidden sm:block max-w-[120px] text-left">
          <div className="text-[10px] text-ink-400 leading-none">已登录</div>
          <div className="text-sm font-medium text-ink-800 truncate leading-tight mt-0.5">
            {user?.full_name || user?.email}
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-ink-400 transition-transform duration-200 ${menuOpen ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {menuOpen && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-2 w-64 rounded-2xl dropdown-surface py-2 z-50 animate-dropdown"
        >
          <div className="px-4 py-2.5 border-b border-black/5">
            <p className="text-sm font-medium text-ink-900 truncate">{user?.full_name || "用户"}</p>
            <p className="text-xs text-ink-400 truncate">{user?.email}</p>
          </div>

          <div className="py-1">
            <Link
              href="/profile"
              role="menuitem"
              className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-ink-700 hover:bg-canvas-100 transition-colors"
            >
              <svg className="w-4 h-4 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.678 0-5.243-.465-7.499-1.632z" />
              </svg>
              个人中心
            </Link>

            <button
              onClick={toggleTheme}
              role="menuitem"
              className="w-full flex items-center justify-between gap-2.5 px-4 py-2.5 text-sm text-ink-700 hover:bg-canvas-100 transition-colors"
            >
              <span className="flex items-center gap-2.5">
                <svg className="w-4 h-4 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  {theme === "light" ? (
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.373-.386l1.591-1.591M3 12H5.25m.386-4.373l1.591 1.591M12 7.5a4.5 4.5 0 100 9 4.5 4.5 0 000-9z" />
                  )}
                </svg>
                {theme === "light" ? "切换到夜间" : "切换到白天"}
              </span>
              <span className="text-[10px] text-ink-400 uppercase tracking-wider">{theme === "light" ? "Light" : "Dark"}</span>
            </button>

            <a
              href="https://beian.miit.gov.cn/"
              target="_blank"
              rel="noreferrer"
              role="menuitem"
              className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-ink-700 hover:bg-canvas-100 transition-colors"
            >
              <svg className="w-4 h-4 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              ICP 备案信息
            </a>
          </div>

          <div className="border-t border-black/5 pt-1">
            <button
              onClick={handleLogout}
              role="menuitem"
              className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-rose-700 hover:bg-rose-50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
              </svg>
              退出登录
            </button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      <div className="h-[2px] bg-gradient-to-r from-primary-300 via-sage-300 to-rose-300" />

      <nav className="sticky top-0 z-40 navbar-surface">
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
                  const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href))
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`relative inline-flex items-center rounded-full px-4 py-2 text-sm font-medium transition-all duration-200 ${
                        isActive
                          ? "bg-canvas-500 text-ink-900 shadow-sm"
                          : "text-ink-500 hover:text-ink-800 hover:bg-canvas-100"
                      }`}
                    >
                      {link.label}
                    </Link>
                  )
                })}
              </div>
            </div>

            <div className="flex items-center gap-3 flex-shrink-0">
              {isLoading ? (
                <div className="h-9 w-24 rounded-full bg-canvas-200 animate-pulse" />
              ) : user ? (
                <UserMenu />
              ) : (
                <Link href="/login" className="btn-primary rounded-full px-5 py-2.5">
                  登录
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>
    </>
  );
}
