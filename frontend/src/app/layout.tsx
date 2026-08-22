import type { Metadata } from 'next'
import Navbar from '@/components/Navbar'
import ClientProviders from '@/components/ClientProviders'
import './globals.css'

export const metadata: Metadata = {
  title: 'OutEye Edu - 学术桌面操作系统',
  description: '面向外国语言文学一流学科建设的智能教研操作系统',
}

// 防 FOUC：在 hydration 前根据 localStorage 或 prefers-color-scheme 设置主题
const themeInitScript = `
(function() {
  try {
    var saved = localStorage.getItem('theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var theme = saved || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
`

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="font-sans text-ink-900">
        <ClientProviders>
          <div className="app-shell desk-wash">
            <Navbar />

            <main className="relative">
              <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
                <div className="absolute right-[-8%] top-[-4%] h-[28rem] w-[28rem] rounded-full bg-primary-200/20 blur-3xl" />
                <div className="absolute left-[-10%] top-[24%] h-[20rem] w-[20rem] rounded-full bg-rose-200/20 blur-3xl" />
                <div className="absolute bottom-[8%] right-[18%] h-[14rem] w-[14rem] rounded-full bg-sage-200/20 blur-3xl" />
              </div>
              {children}
            </main>

            <footer className="mt-16 footer-surface">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="flex flex-col gap-3 text-center sm:text-left sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <div className="flex items-center justify-center sm:justify-start gap-2 text-ink-500 mb-1.5">
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                      <span className="text-sm font-semibold tracking-tight">OutEye Edu</span>
                    </div>
                    <p className="text-xs text-ink-400 max-w-xl">
                      Academic Desktop OS · 面向外国语言文学一流学科建设的智能教研操作系统
                    </p>
                  </div>
                  <div className="text-xs text-ink-300 space-y-1">
                    <p>&copy; 2026 OutEye Edu 1.0</p>
                    <p>{`挑战杯"揭榜挂帅"专项赛`}</p>
                  </div>
                </div>
                <a
                  href="https://beian.miit.gov.cn/"
                  target="_blank"
                  rel="noreferrer"
                  className="mt-5 block text-center text-xs text-ink-300 transition-colors hover:text-ink-500"
                >
                  鲁ICP备2026044330号-1
                </a>
              </div>
            </footer>
          </div>
        </ClientProviders>
      </body>
    </html>
  )
}
