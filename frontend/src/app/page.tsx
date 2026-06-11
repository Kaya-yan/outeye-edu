import Link from 'next/link'

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* 英雄区域 */}
      <div className="text-center">
        <h1 className="text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
          <span className="block xl:inline">OutEye Edu 1.0</span>
          <span className="block text-primary-600 xl:inline">智能教研操作系统</span>
        </h1>
        <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
          面向外国语言文学一流学科建设，融合RAG与LLM Wiki技术，实现从"经验驱动"到"理论驱动+数据驱动"的教研范式升级。
        </p>
        <div className="mt-5 max-w-md mx-auto sm:flex sm:justify-center md:mt-8">
          <div className="rounded-md shadow">
            <Link href="/analysis" className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 md:py-4 md:text-lg md:px-10">
              开始分析
            </Link>
          </div>
          <div className="mt-3 rounded-md shadow sm:mt-0 sm:ml-3">
            <Link href="/projects" className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-primary-600 bg-white hover:bg-gray-50 md:py-4 md:text-lg md:px-10">
              我的项目
            </Link>
          </div>
        </div>
      </div>

      {/* 特性介绍 */}
      <div className="mt-24">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-gray-900">核心功能</h2>
          <p className="mt-4 max-w-2xl mx-auto text-xl text-gray-500">
            基于12大语言学理论的工程化实现
          </p>
        </div>

        <div className="mt-12 grid gap-8 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
          {/* 特性1 */}
          <div className="card hover:shadow-lg transition-shadow duration-300">
            <div className="text-primary-600 mb-4">
              <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900">智能课文分析</h3>
            <p className="mt-2 text-base text-gray-500">
              六维分析报告：词汇、句法、语篇、认知负荷、学习者适配、教学建议
            </p>
          </div>

          {/* 特性2 */}
          <div className="card hover:shadow-lg transition-shadow duration-300">
            <div className="text-primary-600 mb-4">
              <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900">教案自动生成</h3>
            <p className="mt-2 text-base text-gray-500">
              基于Bloom分类学和Krashen i+1理论的智能教学设计
            </p>
          </div>

          {/* 特性3 */}
          <div className="card hover:shadow-lg transition-shadow duration-300">
            <div className="text-primary-600 mb-4">
              <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900">知识检索</h3>
            <p className="mt-2 text-base text-gray-500">
              RAG驱动的智能文献推荐，支持对立观点和交叉引用
            </p>
          </div>

          {/* 特性4 */}
          <div className="card hover:shadow-lg transition-shadow duration-300">
            <div className="text-primary-600 mb-4">
              <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900">理论工程化</h3>
            <p className="mt-2 text-base text-gray-500">
              12大语言学理论的可计算、可执行、可验证实现
            </p>
          </div>
        </div>
      </div>

      {/* 技术架构 */}
      <div className="mt-24">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-gray-900">混合架构</h2>
          <p className="mt-4 max-w-2xl mx-auto text-xl text-gray-500">
            RAG + LLM Wiki 双引擎驱动
          </p>
        </div>

        <div className="mt-12 bg-white rounded-lg shadow-lg p-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-primary-600 mb-4">
                <svg className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900">Layer 1: LLM Wiki</h3>
              <p className="mt-2 text-sm text-gray-500">
                知识编译层<br />
                12大理论实体页<br />
                结构化知识图谱
              </p>
            </div>

            <div className="text-center">
              <div className="text-primary-600 mb-4">
                <svg className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900">Layer 2: RAG</h3>
              <p className="mt-2 text-sm text-gray-500">
                灵活检索层<br />
                Qdrant向量库<br />
                实时语义检索
              </p>
            </div>

            <div className="text-center">
              <div className="text-primary-600 mb-4">
                <svg className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900">Layer 3: 应用层</h3>
              <p className="mt-2 text-sm text-gray-500">
                智能教研应用<br />
                课文分析引擎<br />
                教案生成系统
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 12大理论 */}
      <div className="mt-24">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-gray-900">12大理论支撑</h2>
          <p className="mt-4 max-w-2xl mx-auto text-xl text-gray-500">
            从理论到实践的工程化转化
          </p>
        </div>

        <div className="mt-12 grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {[
            { name: 'Lexile Framework', desc: '阅读能力量化' },
            { name: 'Flesch-Kincaid', desc: '可读性评估' },
            { name: 'CEFR', desc: '语言能力分级' },
            { name: 'Krashen i+1', desc: '输入假说' },
            { name: '认知负荷理论', desc: '认知负荷管理' },
            { name: 'Noticing假说', desc: '注意假说' },
            { name: 'Bloom分类学', desc: '认知层级' },
            { name: 'ZPD/支架理论', desc: '最近发展区' },
            { name: '体裁分析', desc: 'CARS模型' },
            { name: 'RST修辞结构', desc: '核-卫星关系' },
            { name: '主位推进理论', desc: '信息流动' },
            { name: '批判性思维', desc: 'Paul&Elder' },
          ].map((theory, index) => (
            <div key={index} className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow duration-300">
              <h4 className="font-medium text-gray-900">{theory.name}</h4>
              <p className="text-sm text-gray-500 mt-1">{theory.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="mt-24 bg-primary-700 rounded-lg shadow-xl overflow-hidden">
        <div className="px-6 py-12 sm:px-12 sm:py-16 lg:px-16">
          <div className="text-center">
            <h2 className="text-3xl font-extrabold text-white">
              开始使用 OutEye Edu
            </h2>
            <p className="mt-4 text-lg leading-6 text-primary-200">
              体验智能教研的未来，提升教学效率与质量
            </p>
            <Link href="/analysis" className="mt-8 inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-primary-600 bg-white hover:bg-primary-50 md:py-4 md:text-lg md:px-10">
              立即开始
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}