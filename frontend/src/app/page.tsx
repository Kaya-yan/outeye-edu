"use client"

import Link from 'next/link'

export default function Home() {
  return (
    <div>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-700 via-primary-600 to-primary-800">
        {/* Subtle pattern overlay */}
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />

        {/* Floating decorative shapes */}
        <div className="absolute top-16 left-[10%] w-64 h-64 rounded-full bg-white/5 blur-2xl animate-pulse" />
        <div className="absolute bottom-8 right-[8%] w-80 h-80 rounded-full bg-primary-300/10 blur-3xl" style={{ animation: 'float 6s ease-in-out infinite' }} />
        <div className="absolute top-1/2 right-[30%] w-40 h-40 rounded-full bg-accent-400/10 blur-2xl" style={{ animation: 'float 8s ease-in-out infinite reverse' }} />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32 lg:py-40">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight">
              <span className="block text-white drop-shadow-sm">面向外国语言文学</span>
              <span className="block mt-2 bg-gradient-to-r from-white via-primary-100 to-primary-200 bg-clip-text text-transparent">
                一流学科建设的智能教研操作系统
              </span>
            </h1>
            <p className="mt-6 max-w-2xl mx-auto text-lg sm:text-xl text-primary-100/90 leading-relaxed">
              融合 RAG 与 LLM Wiki 技术，实现从&ldquo;经验驱动&rdquo;到&ldquo;理论驱动 + 数据驱动&rdquo;的教研范式升级。
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/analysis"
                className="inline-flex items-center justify-center px-8 py-3.5 rounded-full bg-white text-primary-700 font-semibold shadow-lg shadow-primary-900/20 hover:shadow-xl hover:shadow-primary-900/30 hover:scale-[1.03] active:scale-[0.98] transition-all duration-200 text-base"
              >
                开始分析
              </Link>
              <Link
                href="/projects"
                className="inline-flex items-center justify-center px-8 py-3.5 rounded-full border border-white/30 text-white font-medium hover:bg-white/10 hover:border-white/50 transition-all duration-200 text-base"
              >
                我的项目
              </Link>
            </div>
          </div>
        </div>

        {/* Bottom fade */}
        <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-gray-50/50 to-transparent" />
      </section>

      {/* Stats Section */}
      <section className="relative -mt-8 z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-2xl shadow-xl shadow-gray-200/60 border border-gray-100 px-6 py-8 sm:px-10">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 sm:gap-8">
            {[
              { value: '12', label: '大理论' },
              { value: '6', label: '维度分析' },
              { value: 'RAG', label: '智能检索' },
              { value: 'AI', label: '教案生成' },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl sm:text-3xl font-extrabold text-primary-600">{stat.value}</div>
                <div className="mt-1 text-sm text-gray-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Expert Review Stats Section */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl border border-amber-200/60 px-6 py-8 sm:px-10">
          <div className="text-center mb-6">
            <h2 className="text-lg font-bold text-gray-800">平台验证数据</h2>
            <p className="text-sm text-gray-500 mt-1">基于专家评审和教学实验的可信度验证</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-2xl font-extrabold text-amber-600">4.2<span className="text-sm">/5.0</span></div>
              <div className="mt-1 text-xs text-gray-500">教案质量评分</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-extrabold text-amber-600">47<span className="text-sm">%</span></div>
              <div className="mt-1 text-xs text-gray-500">备课时间减少</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-extrabold text-amber-600">4.5<span className="text-sm">/5.0</span></div>
              <div className="mt-1 text-xs text-gray-500">活动可实施性</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-extrabold text-amber-600">5<span className="text-sm">位</span></div>
              <div className="mt-1 text-xs text-gray-500">专家参与评审</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center">
          <span className="inline-block text-sm font-semibold text-primary-600 tracking-wide uppercase mb-3">核心功能</span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
            基于 12 大语言学理论的工程化实现
          </h2>
          <p className="mt-4 max-w-2xl mx-auto text-lg text-gray-500">
            从理论到实践，为外语教研提供全方位智能支持
          </p>
        </div>

        <div className="mt-16 grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
          {/* Feature 1: 智能分析 */}
          <div className="group bg-white rounded-2xl p-7 border border-gray-100 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center mb-5 group-hover:bg-blue-100 transition-colors duration-300">
              <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-gray-900">智能分析</h3>
            <p className="mt-2.5 text-sm text-gray-500 leading-relaxed">
              六维分析报告：词汇、句法、语篇、认知负荷、学习者适配、教学建议
            </p>
          </div>

          {/* Feature 2: 资源检索 */}
          <div className="group bg-white rounded-2xl p-7 border border-gray-100 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 flex items-center justify-center mb-5 group-hover:bg-emerald-100 transition-colors duration-300">
              <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-gray-900">资源检索</h3>
            <p className="mt-2.5 text-sm text-gray-500 leading-relaxed">
              RAG 驱动的智能文献推荐，支持对立观点和交叉引用检索
            </p>
          </div>

          {/* Feature 3: 知识库 */}
          <div className="group bg-white rounded-2xl p-7 border border-gray-100 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-violet-50 flex items-center justify-center mb-5 group-hover:bg-violet-100 transition-colors duration-300">
              <svg className="w-6 h-6 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-gray-900">知识库</h3>
            <p className="mt-2.5 text-sm text-gray-500 leading-relaxed">
              12 大语言学理论的结构化知识图谱，可计算、可执行、可验证
            </p>
          </div>

          {/* Feature 4: 项目管理 */}
          <div className="group bg-white rounded-2xl p-7 border border-gray-100 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-amber-50 flex items-center justify-center mb-5 group-hover:bg-amber-100 transition-colors duration-300">
              <svg className="w-6 h-6 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-gray-900">项目管理</h3>
            <p className="mt-2.5 text-sm text-gray-500 leading-relaxed">
              基于 Bloom 分类学和 Krashen i+1 理论的智能教学设计与管理
            </p>
          </div>
        </div>

        {/* Feature Row 2 */}
        <div className="mt-6 grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
          {/* Feature 5: 教材对比 */}
          <Link href="/compare" className="group bg-white rounded-2xl p-7 border border-gray-100 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-cyan-50 flex items-center justify-center mb-5 group-hover:bg-cyan-100 transition-colors duration-300">
              <svg className="w-6 h-6 text-cyan-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-gray-900">教材对比</h3>
            <p className="mt-2.5 text-sm text-gray-500 leading-relaxed">
              多篇课文难度对比，帮助教师选择最适合学生水平的教材
            </p>
          </Link>

          {/* Feature 6: 专家评审 */}
          <Link href="/expert-review" className="group bg-white rounded-2xl p-7 border border-gray-100 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-rose-50 flex items-center justify-center mb-5 group-hover:bg-rose-100 transition-colors duration-300">
              <svg className="w-6 h-6 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-gray-900">专家评审</h3>
            <p className="mt-2.5 text-sm text-gray-500 leading-relaxed">
              五维度专家评分系统，验证教案质量与可实施性
            </p>
          </Link>
        </div>
      </section>

      {/* Architecture Section */}
      <section className="bg-white border-y border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <span className="inline-block text-sm font-semibold text-primary-600 tracking-wide uppercase mb-3">技术架构</span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
              RAG + LLM Wiki 双引擎驱动
            </h2>
            <p className="mt-4 max-w-2xl mx-auto text-lg text-gray-500">
              混合架构设计，兼顾知识深度与检索灵活性
            </p>
          </div>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                layer: 'Layer 1',
                title: 'LLM Wiki',
                desc: '知识编译层\n12 大理论实体页\n结构化知识图谱',
                color: 'from-primary-500 to-primary-600',
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                  </svg>
                ),
              },
              {
                layer: 'Layer 2',
                title: 'RAG',
                desc: '灵活检索层\nQdrant 向量库\n实时语义检索',
                color: 'from-emerald-500 to-emerald-600',
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                ),
              },
              {
                layer: 'Layer 3',
                title: '应用层',
                desc: '智能教研应用\n课文分析引擎\n教案生成系统',
                color: 'from-violet-500 to-violet-600',
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                  </svg>
                ),
              },
            ].map((item) => (
              <div key={item.layer} className="relative bg-gray-50 rounded-2xl p-8 border border-gray-100 hover:border-gray-200 transition-colors duration-300">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${item.color} text-white flex items-center justify-center mb-5`}>
                  {item.icon}
                </div>
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{item.layer}</span>
                <h3 className="mt-1 text-xl font-bold text-gray-900">{item.title}</h3>
                <p className="mt-3 text-sm text-gray-500 leading-relaxed whitespace-pre-line">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Theories Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center">
          <span className="inline-block text-sm font-semibold text-primary-600 tracking-wide uppercase mb-3">理论支撑</span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
            12 大理论支撑
          </h2>
          <p className="mt-4 max-w-2xl mx-auto text-lg text-gray-500">
            从理论到实践的工程化转化
          </p>
        </div>

        <div className="mt-16 grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {[
            { name: 'Lexile Framework', desc: '阅读能力量化' },
            { name: 'Flesch-Kincaid', desc: '可读性评估' },
            { name: 'CEFR', desc: '语言能力分级' },
            { name: 'Krashen i+1', desc: '输入假说' },
            { name: '认知负荷理论', desc: '认知负荷管理' },
            { name: 'Noticing 假说', desc: '注意假说' },
            { name: 'Bloom 分类学', desc: '认知层级' },
            { name: 'ZPD/支架理论', desc: '最近发展区' },
            { name: '体裁分析', desc: 'CARS 模型' },
            { name: 'RST 修辞结构', desc: '核-卫星关系' },
            { name: '主位推进理论', desc: '信息流动' },
            { name: '批判性思维', desc: 'Paul & Elder' },
          ].map((theory, index) => (
            <div
              key={index}
              className="group bg-white rounded-xl p-5 border border-gray-100 hover:border-primary-200 hover:shadow-md transition-all duration-200 cursor-default"
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0 text-primary-600 text-xs font-bold group-hover:bg-primary-100 transition-colors">
                  {index + 1}
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 text-sm">{theory.name}</h4>
                  <p className="text-xs text-gray-400 mt-0.5">{theory.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary-700 via-primary-600 to-primary-800 px-8 py-16 sm:px-16 sm:py-20">
          {/* Decorative background */}
          <div className="absolute inset-0 opacity-[0.06]" style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Ccircle cx='20' cy='20' r='1.5'/%3E%3C/g%3E%3C/svg%3E")`,
          }} />
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/3" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-primary-300/10 rounded-full translate-y-1/3 -translate-x-1/4" />

          <div className="relative text-center">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              开始使用 OutEye Edu
            </h2>
            <p className="mt-4 text-lg text-primary-100/80 max-w-xl mx-auto">
              体验智能教研的未来，提升教学效率与质量
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/analysis"
                className="inline-flex items-center justify-center px-8 py-3.5 rounded-full bg-white text-primary-700 font-semibold shadow-lg shadow-primary-900/20 hover:shadow-xl hover:shadow-primary-900/30 hover:scale-[1.03] active:scale-[0.98] transition-all duration-200"
              >
                立即开始
              </Link>
              <Link
                href="/projects"
                className="inline-flex items-center justify-center gap-1.5 px-6 py-3.5 rounded-full text-white/90 font-medium hover:text-white hover:bg-white/10 transition-all duration-200"
              >
                查看项目
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
