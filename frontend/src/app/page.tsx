"use client"

import Link from 'next/link'

const featureCards = [
  {
    title: '智能分析',
    desc: '六维分析报告：词汇、句法、语篇、认知负荷、学习者适配、教学建议',
    href: '/analysis',
    color: 'bg-blue-50 text-primary-600',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
      </svg>
    ),
  },
  {
    title: '资源检索',
    desc: 'RAG 驱动的教学资源推荐，支持对立观点和交叉引用检索',
    href: '/resources',
    color: 'bg-emerald-50 text-emerald-600',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
      </svg>
    ),
  },
  {
    title: '知识库',
    desc: '12 大语言学理论的结构化知识图谱，可计算、可执行、可验证',
    href: '/knowledge',
    color: 'bg-violet-50 text-violet-600',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
      </svg>
    ),
  },
  {
    title: '项目管理',
    desc: '围绕教学任务、课件版本与研修资产形成连续归档与管理视图',
    href: '/projects',
    color: 'bg-amber-50 text-amber-600',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
      </svg>
    ),
  },
  {
    title: '教材对比',
    desc: '多篇课文难度对比，帮助教师选择最适合学生水平的教材',
    href: '/compare',
    color: 'bg-cyan-50 text-cyan-600',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
      </svg>
    ),
  },
  {
    title: '专家评审',
    desc: '五维度专家评分系统，验证教案质量与活动可实施性',
    href: '/expert-review',
    color: 'bg-rose-50 text-rose-600',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
      </svg>
    ),
  },
]

const architectureLayers = [
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
]

const theories = [
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
]

export default function Home() {
  return (
    <div className="px-4 pb-24 pt-8 sm:px-6 lg:px-8">
      <section className="relative max-w-7xl mx-auto overflow-hidden rounded-[36px] brand-surface px-6 py-10 sm:px-10 sm:py-14 lg:px-12 lg:py-16">
        <div className="absolute -left-8 top-10 h-40 w-40 rounded-full bg-rose-200/30 blur-3xl" />
        <div className="absolute right-0 top-0 h-56 w-56 rounded-full bg-primary-200/30 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-48 w-48 rounded-full bg-sage-200/25 blur-3xl" />

        <div className="relative grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <div>
            <div className="section-title mb-3">Academic Desktop OS</div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight text-ink-900 text-balance">
              把课文分析、教案生成与 HTML 课件展示，收进同一张学术桌面
            </h1>
            <p className="mt-6 max-w-2xl text-base sm:text-lg text-ink-500 leading-8">
              OutEye Edu 的主演示链不再停在“生成一份方案”，而是把分析结果自然推进到课件项目、编辑工作台与课堂展示终态。
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {['课文输入与白盒分析', '双源检索与教学方案', 'HTML 课件编辑与课堂展示'].map((label) => (
                <span key={label} className="drawer-handle bg-white/85 border border-black/5 text-ink-600">
                  {label}
                </span>
              ))}
            </div>
            <div className="mt-8 flex flex-col sm:flex-row gap-4">
              <Link href="/analysis" className="btn-primary rounded-full px-7 py-3.5 text-base">
                进入分析工作台
              </Link>
              <Link href="/courseware" className="btn-secondary rounded-full px-7 py-3.5 text-base">
                查看课件工作台
              </Link>
            </div>
            <p className="mt-4 text-sm text-ink-400">
              推荐演示路径：分析页 → 教学方案 → 生成课件 → 编辑器 → 展示端
            </p>
          </div>

          <div className="relative lg:h-[400px]">
            <div className="grid h-full grid-cols-2 gap-4 lg:grid-cols-[1.05fr_0.95fr]">
              <div className="archive-surface p-5 hover-lift">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-2">Workbench</div>
                <div className="rounded-[24px] bg-canvas-200 p-5 h-full flex flex-col justify-between">
                  <div>
                    <div className="text-lg font-semibold text-ink-900">分析结果台</div>
                    <p className="mt-2 text-sm text-ink-500 leading-6">先沉淀证据，再推进教案与课件，不再把 AI 输出停在一份文本里。</p>
                  </div>
                  <div className="mt-6 rounded-2xl bg-white/80 p-4 shadow-soft space-y-2.5">
                    <div className="flex items-center justify-between text-xs text-ink-500">
                      <span>白盒分析</span>
                      <span>完成</span>
                    </div>
                    <div className="h-2 rounded-full bg-primary-200" />
                    <div className="flex items-center justify-between text-xs text-ink-500">
                      <span>生成课件</span>
                      <span>下一步</span>
                    </div>
                    <div className="h-2 rounded-full bg-sage-200 w-2/3" />
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-4">
                <div className="archive-surface p-5 hover-lift">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-2">Archive</div>
                  <div className="rounded-2xl bg-white p-4 shadow-soft">
                    <div className="text-base font-semibold text-ink-900">课件项目归档</div>
                    <p className="mt-2 text-sm text-ink-500">列表、版本、展示配置与组件沉淀形成连续资产视图。</p>
                  </div>
                </div>
                <div className="archive-surface p-5 hover-lift">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400 mb-2">Presentation</div>
                  <div className="rounded-2xl bg-sage-100/80 p-4 shadow-soft">
                    <div className="text-base font-semibold text-ink-900">课堂展示终态</div>
                    <p className="mt-2 text-sm text-ink-500">从教案到 HTML 课件展示，形成真正可演示、可上课的终点。</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative -mt-6 z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="archive-surface px-6 py-8 sm:px-10">
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4 sm:gap-8">
            {[
              { value: '12', label: '理论基础' },
              { value: '4', label: '分析步骤' },
              { value: '2', label: '课件模式' },
              { value: 'HTML', label: '课堂出口' },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl sm:text-3xl font-extrabold text-primary-600">{stat.value}</div>
                <div className="mt-1 text-sm text-gray-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
        <div className="page-surface-strong px-6 py-7 sm:px-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-2xl">
              <div className="section-title mb-2">Primary Demo Flow</div>
              <h2 className="text-2xl sm:text-3xl font-semibold text-ink-900">先把主演示链讲明白，再展开其余功能</h2>
              <p className="mt-3 text-sm sm:text-base text-ink-500 leading-7">
                第二轮重点不是继续平均介绍所有模块，而是让用户一眼读懂：分析结果如何变成可编辑、可展示、可沉淀的课件项目。
              </p>
            </div>
            <Link href="/courseware" className="btn-secondary rounded-full px-5 py-3 text-sm self-start">
              打开课件工作台
            </Link>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-4">
            {[
              {
                step: '01',
                title: '输入与分析',
                desc: '课文输入后得到白盒结果、学习者差距与教学洞察。',
                href: '/analysis',
              },
              {
                step: '02',
                title: '方案与出口',
                desc: '在教学方案区直接决定是否进入课件工作流。',
                href: '/analysis',
              },
              {
                step: '03',
                title: '课件项目',
                desc: '课件列表与详情页承接项目、版本与展示配置。',
                href: '/courseware',
              },
              {
                step: '04',
                title: '编辑与展示',
                desc: '进入编辑器继续生产，并在展示端进入课堂终态。',
                href: '/courseware',
              },
            ].map((item) => (
              <Link key={item.step} href={item.href} className="archive-card p-5 hover-lift">
                <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Step {item.step}</div>
                <h3 className="mt-3 text-lg font-semibold text-ink-900">{item.title}</h3>
                <p className="mt-2 text-sm text-ink-500 leading-6">{item.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
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
          {featureCards.slice(0, 4).map((item) => (
            <Link key={item.title} href={item.href} className="group bg-white rounded-2xl p-7 border border-gray-100 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
              <div className={`w-12 h-12 rounded-xl ${item.color} flex items-center justify-center mb-5 transition-colors duration-300`}>
                {item.icon}
              </div>
              <h3 className="text-lg font-bold text-gray-900">{item.title}</h3>
              <p className="mt-2.5 text-sm text-gray-500 leading-relaxed">{item.desc}</p>
            </Link>
          ))}
        </div>

        <div className="mt-6 grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
          {featureCards.slice(4).map((item) => (
            <Link key={item.title} href={item.href} className="group bg-white rounded-2xl p-7 border border-gray-100 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
              <div className={`w-12 h-12 rounded-xl ${item.color} flex items-center justify-center mb-5 transition-colors duration-300`}>
                {item.icon}
              </div>
              <h3 className="text-lg font-bold text-gray-900">{item.title}</h3>
              <p className="mt-2.5 text-sm text-gray-500 leading-relaxed">{item.desc}</p>
            </Link>
          ))}
        </div>
      </section>

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
            {architectureLayers.map((item) => (
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
          {theories.map((theory, index) => (
            <div key={theory.name} className="group bg-white rounded-xl p-5 border border-gray-100 hover:border-primary-200 hover:shadow-md transition-all duration-200 cursor-default">
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

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary-700 via-primary-600 to-primary-800 px-8 py-16 sm:px-16 sm:py-20">
          <div className="absolute inset-0 opacity-[0.06]" style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Ccircle cx='20' cy='20' r='1.5'/%3E%3C/g%3E%3C/svg%3E")`,
          }} />
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/3" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-primary-300/10 rounded-full translate-y-1/3 -translate-x-1/4" />

          <div className="relative text-center">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              从分析直接走到课堂展示
            </h2>
            <p className="mt-4 text-lg text-primary-100/80 max-w-xl mx-auto">
              继续沿主演示链进入分析工作台，生成方案后再推进到 HTML 课件编辑与展示终态。
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/analysis"
                className="inline-flex items-center justify-center px-8 py-3.5 rounded-full bg-white text-primary-700 font-semibold shadow-lg shadow-primary-900/20 hover:shadow-xl hover:shadow-primary-900/30 hover:scale-[1.03] active:scale-[0.98] transition-all duration-200"
              >
                进入分析工作台
              </Link>
              <Link
                href="/courseware"
                className="inline-flex items-center justify-center gap-1.5 px-6 py-3.5 rounded-full text-white/90 font-medium hover:text-white hover:bg-white/10 transition-all duration-200"
              >
                查看课件项目
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
