# scripts 使用说明

## 语料清洗管线（任务G1）

公共知识库语料的质量问题（PDF 提取产生的逐字竖排碎行、半句截断、页眉页脚混入）
无法在检索与生成端弥补，必须入库前清洗。清洗逻辑在
`app/services/rag/corpus_clean.py`（可单测的纯函数），本目录脚本负责驱动。

### 1. 审计（只读，可反复跑）

```bash
cd backend
PYTHONIOENCODING=utf-8 python scripts/corpus_audit.py
# 复检新库（清洗后应接近全绿）
PYTHONIOENCODING=utf-8 python scripts/corpus_audit.py --collection teaching_knowledge_v2
```

输出：总 chunk 数、五类问题（letter_spine / mid_sentence / noise_lines /
too_short / lang_anomaly）数量与占比、每类抽样 10 条。

### 2. 清洗与重建

```bash
# 第一步：先空跑看前后对照，不写任何数据
PYTHONIOENCODING=utf-8 python scripts/corpus_clean.py --dry-run
# 第二步：正式清洗（含英文黏连块的 LLM 修复，走现有 DeepSeek 通道）
PYTHONIOENCODING=utf-8 python scripts/corpus_clean.py --llm-repair \
    --quarantine-file quarantine_report.json
```

行为：

- **旧 collection 一律不动**，清洗后数据写入新 collection（默认
  `teaching_knowledge_v2`，`--target` 可改）；
- scope=system 文档：逐字碎行合并 → NFKC/零宽/页码页眉清理 → 句边界重切
  （200-800 字符、重叠 1 句、禁止切句）→ 质量过滤（不合格进
  `quarantine_report.json`，不删除但不入库）→ 重新 embedding → 入库；
- scope=private 用户文档原样搬运（保留原向量），切库不丢个人资料；
- `--llm-repair` 只处理「英文逐字母黏连」的隔离块，修复成功的入库并标
  `payload.cleaned_by_llm=true`；
- 英文逐字碎行合并后无法确定性还原空格（如 "slargelyamatter"），
  不开 `--llm-repair` 时此类块一律隔离，不会带病入库。

### 3. 验证与切换（回滚保险）

```bash
# ① 复检：新库五类问题应接近 0
PYTHONIOENCODING=utf-8 python scripts/corpus_audit.py --collection teaching_knowledge_v2
# ② 抽样确认可读后，改服务器 .env 并重启后端
#    QDRANT_COLLECTION=teaching_knowledge_v2
# ③ 回滚：QDRANT_COLLECTION 改回 outeye_knowledge 重启即可（旧库未动）
```

### 赛后语料迭代

新语料入库建议沿用同一管线：先 `corpus_audit.py` 看质量 → 不达标跑
`corpus_clean.py` 灌入干净库 → 切换环境变量。展示层已有句边界修剪兜底
（`excerpt_by_sentence`），个别漏网 chunk 不会在资料抽屉展示断头断尾。

## 其他脚本

- `reseed_knowledge.py` 重建系统知识种子（scope=system）
- `prompt_regression.py` 提示词回归（改 `app/prompts/*.md` 后必跑）
- `smoke_*.py` 各链路冒烟（章节骨架/蓝图/评审/编辑器拖拽/移动端视口等）
