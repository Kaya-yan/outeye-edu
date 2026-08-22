/**
 * 白盒分析术语字典
 *
 * 用于 TermTooltip 组件：用户 hover / focus 术语时显示小弹层。
 * 每条结构：
 *   - definition：一句话定义（学术准确）
 *   - interpretation：数值解读提示（怎么读这个数）
 *   - teaching：教学含义（这个数对课堂意味着什么）
 */

export interface GlossaryEntry {
  definition: string;
  interpretation?: string;
  teaching?: string;
}

export const glossary: Record<string, GlossaryEntry> = {
  "总词数": {
    definition: "课文中所有可识别词的总数量（含重复）。",
    interpretation: "100-300 词适合单课时精读；500+ 词适合泛读或多课时。",
    teaching: "词数决定课堂节奏：长课文要切片处理，避免学生疲劳。",
  },
  "平均句长": {
    definition: "课文每句的平均词数。",
    interpretation: "12-18 词适合中学；20+ 词偏学术，需支架。",
    teaching: "句长影响解码负荷，长句多时建议预拆从句。",
  },
  "连接密度": {
    definition: "每百词中逻辑连接词（and/but/however/因此/所以等）的数量。",
    interpretation: "5-8/百词属正常；低于 3 偏简单堆叠，高于 10 逻辑密集。",
    teaching: "密度低需补连接词教学；密度高需帮学生梳理逻辑链。",
  },
  "AWL 占比": {
    definition: "Academic Word List 学术词汇表覆盖比例。该词表由 Averil Coxhead 编制，共 570 个词族，是学术英语高频词。",
    interpretation: "5-8% 适合基础学术；10%+ 偏高阶学术文本。",
    teaching: "占比高意味着学生需要先建立学术词汇图，再进入课文。",
  },
  "AWL 学术词": {
    definition: "课文中命中 AWL 学术词表的不重复词数。",
    interpretation: "数量越多，学术色彩越浓。",
    teaching: "可作为重点词汇教学的优先级依据。",
  },
  "不重复词": {
    definition: "课文去重后的独立词数，反映词汇分布广度。",
    interpretation: "与总词数对比可看重复率。",
    teaching: "重复率低说明课文词汇多样，需更多预习时间。",
  },
  "词汇丰富度": {
    definition: "Type-Token Ratio (TTR) 的近似值，= 不重复词 / 总词数。值越高词汇越多样。",
    interpretation: "0.5+ 说明词汇丰富；0.3 以下重复多。",
    teaching: "值高要预留词汇预习时间；值低可加快课文节奏。",
  },
  "TTR 近似": {
    definition: "Type-Token Ratio，词汇丰富度指标，= 不重复词数 / 总词数。",
    interpretation: "1.0 为无重复；0.3 以下重复率高。",
    teaching: "用于判断课文是否适合做词汇密集型教学。",
  },
  "难词数": {
    definition: "超出目标学习者水平（CEFR B2+ 或 AWL 高阶）的词数。",
    interpretation: "课文词数的 5% 以内可控；超过 10% 偏难。",
    teaching: "难词数高要先做词汇预热，再进入课文。",
  },
  "超纲负荷": {
    definition: "课文超出目标 CEFR 等级的词汇占比，反映学习者需要预学的词量。",
    interpretation: "低（<5%）可直入；中（5-10%）需预热；高（>10%）需重构任务。",
  },
  "句子数": {
    definition: "课文被自动切分出的句子总数。",
    interpretation: "结合总词数看平均句长。",
    teaching: "切分异常时（句子数过少）需人工校对课文断句。",
  },
  "Flesch": {
    definition: "Flesch Reading Ease 可读性指数，0-100，越高越易读。",
    interpretation: "60+ 较易；30-60 中等；<30 很难。",
    teaching: "值低要先做支架与解释密度设计，否则课堂推进会卡。",
  },
  "可读性": {
    definition: "Flesch Reading Ease 指数，反映课文阅读难度。",
    interpretation: "60+ 较易进入课堂；<60 需要增加引导。",
    teaching: "可读性低时优先设计预读活动与图示。",
  },
  "长句": {
    definition: "词数大于 30 的句子。",
    interpretation: "占比高说明句法负荷重。",
    teaching: "长句多时要在 PPT 上做从句拆分图示。",
  },
  "超长句": {
    definition: "词数大于 40 的句子，认知负荷显著。",
    interpretation: "出现频次高说明课文偏学术写作。",
    teaching: "超长句要在课堂上慢速处理并板书结构。",
  },
  "段落数": {
    definition: "课文按空行或缩进切出的段落总数。",
    interpretation: "段落数多说明结构密集；少说明长段集中。",
    teaching: "用于设计课堂分段阅读节奏。",
  },
  "结构密度": {
    definition: "段落数与总词数的比值，反映课文信息组织密度。",
    interpretation: "密度高说明每段承载信息多。",
    teaching: "密度高要分段精读，密度低可整篇泛读。",
  },
  "体裁": {
    definition: "课文的语篇类型（如叙述/议论/说明/对话）。",
    interpretation: "由连接词分布与句法特征推断。",
    teaching: "体裁决定教学重点：议论抓论点链，叙述抓情节链。",
  },
  "文本结构": {
    definition: "课文的宏观组织模式（如总-分、问题-解决、对比等）。",
    interpretation: "结构清晰更易教；混合结构需引导识别。",
    teaching: "可在课堂开头画结构图，让学生预期信息走向。",
  },
  "CEFR 词汇分布": {
    definition: "课文词汇按欧洲共同语言参考标准（A1-C2）分级后的占比。",
    interpretation: "基础词（A1-A2）覆盖率高说明课文易；C1+ 词多说明偏难。",
    teaching: "未分级词占比高时，需查词典补充分级或判定为专有名词。",
  },
  "六维分析雷达": {
    definition: "从词汇、句法、语篇、可读性、连接度、学术度六个维度归一化打分，雷达图呈现。",
    interpretation: "面积大说明综合难度高；某维度突出是该维度需重点处理。",
    teaching: "用于一眼判断课文的课堂组织成本。",
  },
  "可读性指数": {
    definition: "Flesch Reading Ease 指数，0-100 分制，越高越易读。",
    interpretation: "90+ 极易；60+ 标准；30-60 难；<30 很难。",
    teaching: "指数低需提前设计支架，否则课堂推进会卡。",
  },
};

/**
 * 取术语的简短解释（前 N 字 + 省略号）
 */
export function getShortDefinition(term: string, maxLen = 60): string | null {
  const entry = glossary[term];
  if (!entry) return null;
  const def = entry.definition;
  return def.length > maxLen ? def.slice(0, maxLen) + "…" : def;
}
