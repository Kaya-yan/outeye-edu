"use client";

import RadarChart from "./charts/RadarChart";
import CefrBarChart from "./charts/CefrBarChart";
import ReadabilityGauge from "./charts/ReadabilityGauge";
import DifficultWordsChart from "./charts/DifficultWordsChart";

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
  A1: "bg-green-100 text-green-800",
  A2: "bg-green-200 text-green-900",
  B1: "bg-yellow-100 text-yellow-800",
  B2: "bg-orange-100 text-orange-800",
  C1: "bg-red-100 text-red-800",
  C2: "bg-red-200 text-red-900",
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
  scientific_text: "学术/科学文本",
  i_plus_2_risk: "难度过高(i+2)",
  i_plus_1_optimal: "最优难度(i+1)",
  high_lexical_diversity: "词汇丰富",
};

export default function WhiteboxResults({ data }: { data: WhiteboxData }) {
  const { vocabulary: v, syntax: s, discourse: d, learner_gap: g } = data;

  return (
    <div className="space-y-6">
      {/* Level Overview */}
      <div className="flex items-center gap-4 flex-wrap">
        {data.language && data.language !== "en" && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">语种</span>
            <span className="px-3 py-1 rounded-full text-sm font-semibold bg-blue-100 text-blue-800">
              {data.language_name || data.language}
            </span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">课文等级</span>
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${LEVEL_COLORS[data.text_level] || "bg-gray-100"}`}>
            {data.text_level}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">学生水平</span>
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${LEVEL_COLORS[g.student_level] || "bg-gray-100"}`}>
            {g.student_level}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">差距</span>
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
            g.gap === "i+0" ? "bg-green-100 text-green-800" :
            g.gap === "i+1" ? "bg-yellow-100 text-yellow-800" :
            "bg-red-100 text-red-800"
          }`}>
            {g.gap}
          </span>
        </div>
      </div>

      {/* Gap Description */}
      <p className="text-sm text-gray-600 bg-gray-50 rounded-lg px-4 py-3">
        {g.gap_description}
      </p>

      {/* Charts: Radar + CEFR Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span className="w-1 h-4 bg-primary rounded-full" />
            六维分析雷达
          </h3>
          <RadarChart
            vocabulary={v}
            syntax={s}
            discourse={d}
          />
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span className="w-1 h-4 bg-primary rounded-full" />
            CEFR 词汇分布
          </h3>
          <CefrBarChart
            distribution={v.cefr_distribution}
            totalWords={v.total_words}
          />
        </div>
      </div>

      {/* Charts: Readability + Difficult Words */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span className="w-1 h-4 bg-primary rounded-full" />
            可读性指数
          </h3>
          <ReadabilityGauge fleschScore={s.flesch_reading_ease} />
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span className="w-1 h-4 bg-primary rounded-full" />
            难词 Top 10
          </h3>
          {v.difficult_words.length > 0 ? (
            <DifficultWordsChart words={v.difficult_words} />
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">无超纲词</p>
          )}
        </div>
      </div>

      {/* Vocabulary Stats */}
      <Section title="词汇分析">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat label="总词数" value={v.total_words} />
          <Stat label="不重复词" value={v.unique_words} />
          <Stat label="AWL学术词" value={`${v.awl_count} (${(v.awl_ratio * 100).toFixed(1)}%)`} />
          <Stat label="词汇丰富度" value={v.vocabulary_richness.toFixed(2)} />
        </div>
      </Section>

      {/* Syntax Stats */}
      <Section title="句法分析">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <Stat label="句子数" value={s.total_sentences} />
          <Stat label="平均句长" value={`${s.avg_sentence_length} 词`} />
          <Stat label="Flesch可读性" value={s.flesch_reading_ease} />
          <Stat label="长句(>30词)" value={s.long_sentences_count} />
          <Stat label="超长句(>40词)" value={s.very_long_sentences_count} />
        </div>
        <div className="mt-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
          <div className="text-xs text-amber-700 mb-1">
            最长句（第{s.max_sentence.index + 1}句，{s.max_sentence.word_count}词）
          </div>
          <p className="text-sm text-gray-800">{s.max_sentence.preview}</p>
        </div>
      </Section>

      {/* Discourse Stats */}
      <Section title="语篇分析">
        <div className="grid grid-cols-3 gap-3">
          <Stat label="段落数" value={d.paragraph_count} />
          <Stat label="连接词密度" value={`${d.connective_density}/百词`} />
          <Stat label="体裁" value={d.genre_hint} />
          {d.text_structure && <Stat label="文本结构" value={d.text_structure} />}
        </div>
        {d.teaching_points && d.teaching_points.length > 0 && (
          <div className="mt-3">
            <div className="text-xs font-medium text-gray-500 mb-2">教学要点</div>
            <ul className="space-y-1">
              {d.teaching_points.map((point, i) => (
                <li key={i} className="text-xs text-gray-700 flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">{i+1}</span>
                  {point}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      {/* Enhancement Tags */}
      <Section title="增强标签">
        <div className="flex flex-wrap gap-2">
          {data.enhancement_tags.map((tag) => (
            <span
              key={tag}
              className="px-3 py-1 text-xs font-medium rounded-full bg-primary/10 text-primary border border-primary/20"
            >
              {data.tag_labels?.[tag] || TAG_LABELS[tag] || tag}
            </span>
          ))}
        </div>
      </Section>

      {/* Teaching Insights - 教学含义 */}
      {data.teaching_insights && data.teaching_insights.length > 0 && (
        <Section title="教学含义">
          <div className="space-y-3">
            {data.teaching_insights.map((insight, i) => (
              <div key={i} className="rounded-lg border border-gray-200 bg-white p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                    {insight.metric_name}
                  </span>
                  <span className="text-xs font-bold text-primary">{insight.metric_value}</span>
                  {insight.confidence === "high" && (
                    <span className="text-[10px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded">高置信</span>
                  )}
                </div>
                <p className="text-sm text-gray-700 mb-1">{insight.teaching_implication}</p>
                <p className="text-sm text-primary/80 font-medium">{insight.suggested_action}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Cultural Elements */}
      {data.cultural_elements && data.cultural_elements.length > 0 && (
        <Section title="文化背景元素">
          <div className="space-y-2">
            {data.cultural_elements.map((elem, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 border border-amber-200">
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-amber-200 text-amber-800 flex-shrink-0">
                  {elem.category}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-800">{elem.keyword}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{elem.context}</div>
                  <div className="text-xs text-amber-700 mt-1">{elem.explanation}</div>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Teaching Tips */}
      <Section title="教学提示">
        <ul className="space-y-2">
          {data.teaching_tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
              <span className="w-5 h-5 rounded-full bg-accent/20 text-accent flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                {i + 1}
              </span>
              {tip}
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
        <span className="w-1 h-4 bg-primary rounded-full" />
        {title}
      </h3>
      {children}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-50 rounded-lg px-3 py-2">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-sm font-semibold text-gray-800">{value}</div>
    </div>
  );
}
