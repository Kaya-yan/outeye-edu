import type { Metadata } from 'next'
import Navbar from '@/components/Navbar'
import ClientProviders from '@/components/ClientProviders'
import './globals.css'

export const metadata: Metadata = {
  title: 'OutEye Edu - 智能教研操作系统',
  description: '面向外国语言文学一流学科建设的智能教研操作系统',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className="font-sans">
        <ClientProviders>
        <div className="min-h-screen bg-gray-50/50">
          <Navbar />

          {/* Main content */}
          <main>{children}</main>

          {/* Footer */}
          <footer className="mt-auto border-t border-gray-200/60 bg-white/60 backdrop-blur-sm">
            <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
              <div className="flex flex-col items-center gap-2 text-center">
                <div className="flex items-center gap-1.5 text-gray-400">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <span className="text-sm font-medium text-gray-500">OutEye Edu</span>
                </div>
                <p className="text-xs text-gray-400">
                  &copy; 2026 OutEye Edu 1.0 &mdash; 面向外国语言文学一流学科建设的智能教研操作系统
                </p>
                <p className="text-xs text-gray-300">挑战杯"揭榜挂帅"专项赛</p>
              </div>
            </div>
          </footer>
        </div>
        </ClientProviders>
      </body>
    </html>
  )
}
