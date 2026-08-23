"use client";

import RadarChart from "./charts/RadarChart";
import { cefrLabel } from "@/lib/cefr";
import CefrBarChart from "./charts/CefrBarChart";
import ReadabilityGauge from "./charts/ReadabilityGauge";
import DifficultWordsChart from "./charts/DifficultWordsChart";
import TermTooltip from "./TermTooltip";

interface DifficultWord {
  word: string;
  level: string;
  count: number;
  in_awl: boolean;
}

interface TeachingInsight {
  metric_name: string;
  metric_value: string;
  teaching_implication: string;
  suggested_action: string;
  confidence: string;
}

interface CulturalElement {
  category: string;
  keyword: string;
  context: string;
  explanation: string;
}

interface WhiteboxData {
  text_level: string;
  language?: string;
  language_name?: string;
  vocabulary: {
    total_words: number;
    unique_words: number;
    cefr_distribution: Record<string, number>;
    awl_count: number;
    awl_ratio: number;
    difficult_words: DifficultWord[];
    vocabulary_richness: number;
  };
  syntax: {
    total_sentences: number;
    avg_sentence_length: number;
    max_sentence: { preview: string; word_count: number; index: number };
    long_sentences_count: number;
    very_long_sentences_count: number;
    flesch_reading_ease: number;
  };
  discourse: {
    paragraph_count: number;
    connective_density: number;
    genre_hint: string;
    text_structure?: string;
    teaching_points?: string[];
  };
  learner_gap: {
    text_level: string;
    student_level: string;
    gap: string;
    gap_description: string;
  };
  enhancement_tags: string[];
  tag_labels?: Record<string, string>;
  teaching_insights?: TeachingInsight[];
  cultural_elements?: CulturalElement[];
  teaching_tips: string[];
}

const LEVEL_COLORS: Record<string, string> = {
  A1: "bg-sage-100 text-ink-800",
  A2: "bg-sage-200 text-ink-900",
  B1: "bg-accent-100 text-ink-900",
  B2: "bg-accent-200 text-ink-900",
  C1: "bg-rose-100 text-ink-900",
  C2: "bg-rose-200 text-ink-900",
};

const TAG_LABELS: Record<string, string> = {
  high_academic_vocab: "学术词汇密集",
  very_high_academic_vocab: "高密度学术词汇",
  many_difficult_words: "超纲词较多",
  moderate_difficult_words: "中等超纲词",
  very_long_sentences: "超长句",
  long_sentences_present: "长句存在",
  dense_complex_syntax: "复杂句法",
  very_difficult_readability: "可读性很低",
  difficult_readability: "可读性较低",
  high_connective_density: "连接词密集",
  argumentative_text: "议论文",
  scientific_text: "学术 / 科学文本",
  i_plus_2_risk: "难度过高 (i+2)",
  i_plus_1_optimal: "最优难度 (i+1)",
  high_lexical_diversity: "词汇丰富",
};

export default function WhiteboxResults({ data }: { data: WhiteboxData }) {
  const { vocabulary: v, syntax: s, discourse: d, learner_gap: g } = data;

  const readinessTone =
    g.gap === "i+0"
      ? {
          badge: "bg-sage-100 text-ink-800 border border-sage-200",
          title: "当前课文与学生水平基本匹配",
          summary: "可以直接进入教学设计，重点放在课堂节奏与活动组织。",
        }
      : g.gap === "i+1"
        ? {
            badge: "bg-accent-100 text-ink-900 border border-accent-200",
            title: "当前课文位于理想挑战区间",
            summary: "适合继续生成教学方案，并在活动设计中加入必要支架。",
          }
        : {
            badge: "bg-rose-100 text-ink-900 border border-rose-200",
            title: "当前课文对目标学生存在明显难度风险",
            summary: "建议优先关注支架、预教学与任务拆分，再决定课件呈现方式。",
          };

  return (
    <div className="space-y-6">
      <div className="page-surface-strong p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <div className="section-title mb-2">Analysis Verdict</div>
            <h3 className="text-2xl font-semibold text-ink-900">{readinessTone.title}</h3>
            <p className="mt-3 text-sm text-ink-500 leading-7">{g.gap_description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {data.language && data.language !== "en" && (
                <span className="drawer-handle bg-white border border-black/5 text-ink-500">
                  {data.language_name || data.language}
                </span>
              )}
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${LEVEL_COLORS[data.text_level] || "bg-canvas-200 text-ink-800"}`}>
                课文等级 {cefrLabel(data.text_level)}
              </span>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${LEVEL_COLORS[g.student_level] || "bg-canvas-200 text-ink-800"}`}>
                学生水平 {cefrLabel(g.student_level)}
              </span>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${readinessTone.badge}`}>
                学习者差距 {g.gap}
              </span>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:w-[420px]">
            <VerdictCard label="体裁判断" value={d.genre_hint} note={d.text_structure || "等待结构分析"} term="体裁" />
            <VerdictCard label="可读性" value={s.flesch_reading_ease} note={s.flesch_reading_ease > 60 ? "较易进入课堂" : "需增加引导"} term="可读性" />
            <VerdictCard label="重点出口" value="生成课件" note={readinessTone.summary} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard label="总词数" value={v.total_words} note="词汇规模" term="总词数" />
        <MetricCard label="平均句长" value={`${s.avg_sentence_length} 词`} note="句法负荷" term="平均句长" />
        <MetricCard label="连接密度" value={`${d.connective_density}/百词`} note="语篇衔接" term="连接密度" />
        <MetricCard label="AWL 占比" value={`${(v.awl_ratio * 100).toFixed(1)}%`} note="学术词汇" term="AWL 占比" />
      </div>

      <div className="archive-surface p-5 sm:p-6">
        <div className="section-title mb-2">Key Judgement</div>
        <h3 className="text-xl font-semibold text-ink-900">先看最重要的教学判断，再看底层指标</h3>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-3">
            <JudgementCard title="学习者适配" body={readinessTone.summary} tone={g.gap === "i+2" ? "rose" : g.gap === "i+1" ? "accent" : "sage"} />
            {d.teaching_points && d.teaching_points.length > 0 && (
              <JudgementCard
                title="优先教学要点"
                body={d.teaching_points.slice(0, 3).join("；")}
                tone="canvas"
              />
            )}
          </div>
          <div className="space-y-3">
            <JudgementCard
              title="句法负荷"
              body={`长句 ${s.long_sentences_count} 个，超长句 ${s.very_long_sentences_count} 个，最长句位于第 ${s.max_sentence.index + 1} 句。`}
              tone="canvas"
            />
            <JudgementCard
              title="语篇组织"
              body={`共 ${d.paragraph_count} 段，体裁偏向 ${d.genre_hint}${d.text_structure ? `，结构为 ${d.text_structure}` : ""}。`}
              tone="canvas"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartPanel title="六维分析雷达" caption="用于快速判断课文在哪些维度会拉高课堂组织成本。" term="六维分析雷达">
          <RadarChart vocabulary={v} syntax={s} discourse={d} />
        </ChartPanel>
        <ChartPanel title="CEFR 词汇分布" caption="先看基础词覆盖，再看高阶词与未分级词是否集中。" term="CEFR 词汇分布">
          <CefrBarChart distribution={v.cefr_distribution} totalWords={v.total_words} />
        </ChartPanel>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartPanel title="可读性指数" caption="可读性越低，越需要提前设计支架与解释密度。" term="可读性指数">
          <ReadabilityGauge fleschScore={s.flesch_reading_ease} />
        </ChartPanel>
        <ChartPanel title="难词 Top 10" caption="重点看超纲词是否会直接影响课堂目标与任务推进。">
          {v.difficult_words.length > 0 ? (
            <DifficultWordsChart words={v.difficult_words} />
          ) : (
            <div className="h-64 flex items-center justify-center text-sm text-ink-400">当前无明显超纲词</div>
          )}
        </ChartPanel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <EvidencePanel title="词汇证据" subtitle="Vocabulary">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="不重复词" value={v.unique_words} note="词汇分布" term="不重复词" />
            <MetricCard label="词汇丰富度" value={v.vocabulary_richness.toFixed(2)} note="TTR 近似" term="词汇丰富度" />
            <MetricCard label="AWL 学术词" value={v.awl_count} note="高阶词项" term="AWL 学术词" />
            <MetricCard label="难词数" value={v.difficult_words.length} note="超纲负荷" term="难词数" />
          </div>
        </EvidencePanel>

        <EvidencePanel title="句法证据" subtitle="Syntax">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="句子数" value={s.total_sentences} note="文本切分" term="句子数" />
            <MetricCard label="Flesch" value={s.flesch_reading_ease} note="可读性" term="Flesch" />
            <MetricCard label="长句" value={s.long_sentences_count} note="> 30 词" term="长句" />
            <MetricCard label="超长句" value={s.very_long_sentences_count} note="> 40 词" term="超长句" />
          </div>
          <div className="mt-4 rounded-2xl bg-canvas-100/80 border border-black/5 px-4 py-3">
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">最长句</div>
            <p className="mt-2 text-sm text-ink-700 leading-6">{s.max_sentence.preview}</p>
          </div>
        </EvidencePanel>

        <EvidencePanel title="语篇证据" subtitle="Discourse">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="段落数" value={d.paragraph_count} note="结构密度" term="段落数" />
            <MetricCard label="连接密度" value={`${d.connective_density}`} note="每百词" term="连接密度" />
            <MetricCard label="体裁" value={d.genre_hint} note="文本类型" term="体裁" />
            <MetricCard label="文本结构" value={d.text_structure || "待定"} note="结构判断" term="文本结构" />
          </div>
        </EvidencePanel>
      </div>

      <EvidencePanel title="增强标签" subtitle="Enhancement Tags">
        <div className="flex flex-wrap gap-2">
          {data.enhancement_tags.map((tag) => (
            <span key={tag} className="px-3 py-1 text-xs font-medium rounded-full bg-primary-100 text-ink-800 border border-primary-200">
              {data.tag_labels?.[tag] || TAG_LABELS[tag] || tag}
            </span>
          ))}
        </div>
      </EvidencePanel>

      {data.teaching_insights && data.teaching_insights.length > 0 && (
        <EvidencePanel title="教学洞察" subtitle="Insights">
          <div className="space-y-3">
            {data.teaching_insights.map((insight, i) => (
              <div key={i} className="rounded-2xl border border-black/5 bg-white p-4 shadow-soft">
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className="drawer-handle bg-canvas-100 border border-black/5 text-ink-500">{insight.metric_name}</span>
                  <span className="text-sm font-semibold text-ink-900">{insight.metric_value}</span>
                  {insight.confidence === "high" && (
                    <span className="drawer-handle bg-sage-100 border border-sage-200 text-ink-700">高置信</span>
                  )}
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <InsightCell label="指标含义" value={insight.metric_name} />
                  <InsightCell label="教学影响" value={insight.teaching_implication} />
                  <InsightCell label="建议动作" value={insight.suggested_action} highlight />
                </div>
              </div>
            ))}
          </div>
        </EvidencePanel>
      )}

      {data.cultural_elements && data.cultural_elements.length > 0 && (
        <EvidencePanel title="文化背景元素" subtitle="Context">
          <div className="space-y-2">
            {data.cultural_elements.map((elem, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-2xl bg-accent-50 border border-accent-100">
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-accent-200 text-ink-900 flex-shrink-0">
                  {elem.category}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-ink-900">{elem.keyword}</div>
                  <div className="text-xs text-ink-400 mt-0.5">{elem.context}</div>
                  <div className="text-xs text-ink-600 mt-1 leading-6">{elem.explanation}</div>
                </div>
              </div>
            ))}
          </div>
        </EvidencePanel>
      )}

      <EvidencePanel title="教学提示" subtitle="Teaching Tips">
        <ul className="space-y-2">
          {data.teaching_tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-3 text-sm text-ink-700 leading-6">
              <span className="w-6 h-6 rounded-full bg-primary-100 text-ink-800 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                {i + 1}
              </span>
              {tip}
            </li>
          ))}
        </ul>
      </EvidencePanel>
    </div>
  );
}

function ChartPanel({ title, caption, children, term }: { title: string; caption: string; children: React.ReactNode; term?: string }) {
  return (
    <div className="archive-surface p-5">
      <div className="section-title mb-2">Evidence View</div>
      <h3 className="text-lg font-semibold text-ink-900">
        {term ? <TermTooltip term={term}>{title}</TermTooltip> : title}
      </h3>
      <p className="mt-2 text-sm text-ink-500 leading-6">{caption}</p>
      <div className="mt-5">{children}</div>
    </div>
  );
}

function EvidencePanel({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="archive-surface p-5 sm:p-6">
      <div className="section-title mb-2">{subtitle}</div>
      <h3 className="text-lg font-semibold text-ink-900">{title}</h3>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function VerdictCard({ label, value, note, term }: { label: string; value: string | number; note: string; term?: string }) {
  return (
    <div className="data-card p-4 bg-white/90">
      <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">
        {term ? <TermTooltip term={term} block>{label}</TermTooltip> : label}
      </div>
      <div className="mt-2 text-lg font-semibold text-ink-900">{value}</div>
      <p className="mt-1 text-xs text-ink-500 leading-5">{note}</p>
    </div>
  );
}

function MetricCard({ label, value, note, term }: { label: string; value: string | number; note: string; term?: string }) {
  return (
    <div className="data-card p-4 bg-white/92">
      <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">
        {term ? <TermTooltip term={term} block>{label}</TermTooltip> : label}
      </div>
      <div className="mt-2 text-lg font-semibold text-ink-900">{value}</div>
      <div className="mt-1 text-xs text-ink-500">{note}</div>
    </div>
  );
}

function JudgementCard({ title, body, tone }: { title: string; body: string; tone: "sage" | "accent" | "rose" | "canvas" }) {
  const toneClass = {
    sage: "bg-sage-50 border-sage-200",
    accent: "bg-accent-50 border-accent-200",
    rose: "bg-rose-50 border-rose-200",
    canvas: "bg-canvas-100/80 border-black/5",
  }[tone];

  return (
    <div className={`rounded-2xl border px-4 py-4 ${toneClass}`}>
      <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">{title}</div>
      <p className="mt-2 text-sm text-ink-700 leading-6">{body}</p>
    </div>
  );
}

function InsightCell({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-2xl border px-3 py-3 ${highlight ? "bg-sage-50 border-sage-200" : "bg-canvas-100/70 border-black/5"}`}>
      <div className="text-[11px] uppercase tracking-[0.16em] text-ink-400">{label}</div>
      <p className={`mt-2 text-sm leading-6 ${highlight ? "text-ink-900 font-medium" : "text-ink-700"}`}>{value}</p>
    </div>
  );
}
