"""
生成 theory.json 理论文献元数据清单

数据来源：
- 0729 目录 10 篇：自动从 理论文献.docx 提取（结构化摘要）
- 0811 教学理论目录 17 篇：手填（已从 PDF 内容提取真实作者/标题）

输出：backend/scripts/manifests/theory.json

用法：
    python backend/scripts/manifests/generate_theory_manifest.py
"""

import json
import os
import re
import sys
from pathlib import Path

import docx

SEED_MATERIALS_ROOT = Path(r"C:\Users\ht\Documents\outeye3.0\seed-materials")
DOCX_PATH = SEED_MATERIALS_ROOT / "数据收集（0729）" / "理论" / "理论文献.docx"
OUTPUT_PATH = Path(__file__).parent / "theory.json"


def extract_0729_theory_from_docx() -> list:
    """从 理论文献.docx 提取 0729 目录 10 篇论文的结构化元数据"""
    doc = docx.Document(DOCX_PATH)
    # python-docx 的 paragraph.text 可能包含段落内换行符 \n
    # 把每个段落的 \n 也当作行分隔符，全部展平成单行列表
    raw_paragraphs = [p.text for p in doc.paragraphs]
    paragraphs = []
    for p in raw_paragraphs:
        for line in p.split("\n"):
            line = line.strip()
            if line:
                paragraphs.append(line)

    entries = []
    current = None
    state = None  # 当前正在填充的字段

    for text in paragraphs:
        # 新条目起始：以 "N. 《...》（作者）" 开头
        title_match = re.match(r"^(\d+)\.\s*《(.+?)》\s*[（(]\s*(.+?)\s*[)）]\s*$", text)
        if title_match:
            if current:
                entries.append(current)
            idx = int(title_match.group(1))
            current = {
                "doc_id": f"T-{idx:03d}",
                "batch": "supplementary",
                "title": title_match.group(2).strip(),
                "authors": [a.strip() for a in re.split(r"[、,，]", title_match.group(3)) if a.strip()],
                "theory_tags": [],
                "source_pdf_dir": "0729",
                "raw_entry_index": idx,
            }
            state = None
            continue

        if current is None:
            continue

        # 教学理论：xxx
        m = re.match(r"^教学理论[：:]\s*(.+)$", text)
        if m:
            current["theory_name"] = m.group(1).strip()
            state = "theory_name"
            continue

        # 提出者与时间：xxx
        m = re.match(r"^提出者与时间[：:]\s*(.+)$", text)
        if m:
            current["theorist_and_year"] = m.group(1).strip()
            state = "theorist"
            continue

        # 信息内容：xxx
        m = re.match(r"^信息内容[：:]\s*(.+)$", text)
        if m:
            current["core_content"] = m.group(1).strip()
            state = "content"
            continue

        # 应用示例：xxx
        m = re.match(r"^应用示例[：:]\s*(.+)$", text)
        if m:
            current["application"] = m.group(1).strip()
            state = "application"
            continue

        # 总结：xxx（出现在新条目开头，跳过——已合并到 core_content）
        m = re.match(r"^总结[：:]\s*(.+)$", text)
        if m:
            # 把总结作为简短描述保存（不覆盖 core_content）
            current["summary"] = m.group(1).strip()
            state = "summary"
            continue

        # 注意事项：[1]作者. 标题[J]. 期刊, 年, (期): 页码. 摘要:xxx
        m = re.match(r"^注意事项[：:]\s*\[\d+\]\s*(.+)$", text)
        if m:
            cite_text = m.group(1).strip()
            # 分步解析：先找 [J]. 期刊名 + 年份
            jm = re.search(r"\[J\]\.\s*(.+?),\s*(\d{4})\s*,\s*(.+)", cite_text)
            if jm:
                current["source_journal"] = jm.group(1).strip()
                current["year"] = int(jm.group(2))
                rest = jm.group(3)
                # rest 形如 "27 (1): 63-67." 或 "(S1): 278-280."
                vm = re.match(r"(\d+)\s+", rest)
                if vm:
                    current["volume"] = vm.group(1)
                im = re.search(r"[\(（]\s*(\d+|[Ss]\d+)\s*[\)）]", rest)
                if im:
                    current["issue"] = im.group(1)
                pm = re.search(r":\s*([\d\-]+)", rest)
                if pm:
                    current["pages"] = pm.group(1)
            else:
                # 没匹配上 [J]. 标记，尝试只提取年份
                ym = re.search(r"(\d{4})", cite_text)
                if ym:
                    current["year"] = int(ym.group(1))
            current["raw_citation"] = cite_text
            state = "cite"
            continue

        # 摘要：xxx（紧接注意事项行之后的摘要行）
        m = re.match(r"^摘要[：:]\s*(.+)$", text)
        if m:
            current["abstract"] = m.group(1).strip()
            state = "abstract"
            continue

        # 后续行续接上一字段
        if state == "content":
            current["core_content"] = (current.get("core_content", "") + text).strip()
        elif state == "application":
            current["application"] = (current.get("application", "") + text).strip()
        elif state == "summary":
            current["summary"] = (current.get("summary", "") + text).strip()
        elif state == "cite":
            current["raw_citation"] = (current.get("raw_citation", "") + text).strip()
            # 如果之前没解析出 year，再试一次
            if "year" not in current:
                ym = re.search(r"(\d{4})", current.get("raw_citation", ""))
                if ym:
                    current["year"] = int(ym.group(1))
        elif state == "abstract":
            current["abstract"] = (current.get("abstract", "") + text).strip()

    if current:
        entries.append(current)

    # 关联到 0729 目录的实际 PDF 文件名
    pdf_dir = SEED_MATERIALS_ROOT / "数据收集（0729）" / "理论"
    pdf_files = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")])

    # 用作者姓匹配 PDF 文件名（如 "理论-叶海英-从..." -> 含 "叶海英"）
    for entry in entries:
        for pdf_fn in pdf_files:
            # 提取 PDF 文件名里的作者（"理论-作者-..." 中间字段）
            parts = pdf_fn.replace("理论-", "").split("-")
            if len(parts) >= 1:
                pdf_author = parts[0]
                # entry["authors"] 里有这位作者吗
                if any(pdf_author in a or a in pdf_author for a in entry.get("authors", [])):
                    entry["file_path"] = str(pdf_dir / pdf_fn)
                    entry["original_filename"] = pdf_fn
                    break

    # 推断 theory_tags
    tag_map = {
        "注意假说": ["noticing_hypothesis", "input"],
        "输入假说": ["input_hypothesis", "i_plus_1", "Krashen"],
        "情感过滤": ["affective_filter", "Krashen"],
        "布鲁姆": ["Bloom", "taxonomy", "cognitive_hierarchy"],
        "最近发展区": ["ZPD", "Vygotsky", "scaffolding"],
        "输出假设": ["output_hypothesis", "Swain"],
    }
    for entry in entries:
        theory_name = entry.get("theory_name", "")
        for keyword, tags in tag_map.items():
            if keyword in theory_name:
                entry["theory_tags"] = list(set(entry.get("theory_tags", []) + tags))
        if not entry.get("theory_tags"):
            entry["theory_tags"] = ["untagged"]

    return entries


# 0811 教学理论目录 17 篇真实元数据（从 PDF 内容人工提取）
THEORY_0811 = [
    {
        "doc_id": "T-101",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论1-Tim Johns-DDL-1991.pdf",
        "original_filename": "理论1-Tim Johns-DDL-1991.pdf",
        "title": "基于语料库驱动的对外汉语词汇教学模式研究",
        "authors": ["张栋", "蔡亚薇"],
        "source_journal": "（未在文件名中标明，从内容推断期刊名待补）",
        "year": 2022,
        "issue": "3",
        "pages": "136-140",
        "article_number": "2095-8978(2022)03-0136-05",
        "theory_tags": ["DDL", "corpus", "vocabulary"],
        "theory_name": "数据驱动学习（Data-Driven Learning, DDL）",
        "theorist_and_year": "Tim Johns, 1991（原版提出者）；本篇为中文应用研究",
        "core_content": "以建构主义为理论基础，汉语教师利用母语者真实语料构建微型文本，提供多样化语境、辨析近义词、呈现归纳词语搭配规则，支撑学习者建构汉语词汇知识。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-102",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论2-Tim Johns-DDL-1991.pdf",
        "original_filename": "理论2-Tim Johns-DDL-1991.pdf",
        "title": "语料库数据驱动的外语学习：思想、方法和技术",
        "authors": ["甄凤超"],
        "source_journal": "（待补，从内容看是外语教学类期刊）",
        "year": None,
        "theory_tags": ["DDL", "corpus", "autonomous_learning"],
        "theory_name": "数据驱动学习（DDL）",
        "theorist_and_year": "Tim Johns, 20世纪90年代初（原版提出者）；本篇为中文综述",
        "core_content": "DDL 四大特征：以学生为中心、提供真实语言材料、强调自我探索与发现、自下而上的归纳式学习。实现方法包括：KWIC 检索、分析搭配、类联接和扩展语境、使用主题词和制作课件。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-103",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论3-Fairclough-CDA-1989.pdf",
        "original_filename": "理论3-Fairclough-CDA-1989.pdf",
        "title": "批判话语分析：目标、方法与动态",
        "authors": ["辛斌"],
        "source_journal": "（待补，作者简介显示研究方向为语用学/篇章语义学/批判语言学）",
        "year": None,
        "theory_tags": ["CDA", "critical_discourse", "Fairclough"],
        "theory_name": "批判话语分析（Critical Discourse Analysis, CDA）",
        "theorist_and_year": "Fairclough, 1989（原版提出者）；本篇为中文综述",
        "core_content": "CDA 与批判社会学的目的一致，旨在改变或消除被认为导致不真实或扭曲的意识条件，开启反省过程。本篇分析 CDA 的目标、方法与动态。",
        "_pending_verification": True,
        "_verification_note": "PDF 为 GBK-EUC-H 编码，PyPDF2 乱码；标题与作者系从乱码中可识别字符推断，需在服务器用 PyMuPDF 验证。",
    },
    {
        "doc_id": "T-104",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论4-Hardt-Mautner-DHA-1995.pdf",
        "original_filename": "理论4-Hardt-Mautner-DHA-1995.pdf",
        "title": "基于语料库的“历史语篇分析”（DHA）的过程与价值——以美国主流媒体对希拉里电子邮件门的话语建构为例",
        "authors": ["杨敏", "符小丽"],
        "source_journal": "外国语",
        "year": 2018,
        "issue": "2",
        "pages": "77-85",
        "article_number": "1004-5139(2018)02-0077-09",
        "theory_tags": ["DHA", "discourse_historical", "Wodak", "corpus"],
        "theory_name": "历史语篇分析法（Discourse-Historical Approach, DHA）",
        "theorist_and_year": "Ruth Wodak, 1995（原版提出者）；本篇为中文应用研究",
        "core_content": "DHA 聚焦政治领域话语，包括政治演讲、政治辩论、答记者问及媒体对政治事件的报道。本研究以美国主流媒体对希拉里电子邮件门的话语建构为案例。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-105",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论5-Fairclough-CDA-1989.pdf",
        "original_filename": "理论5-Fairclough-CDA-1989.pdf",
        "title": "基于语料库的批评话语分析",
        "authors": ["郭松"],
        "source_journal": "（待补，从作者机构看是天津商业大学）",
        "year": None,
        "theory_tags": ["CDA", "corpus", "qualitative", "quantitative"],
        "theory_name": "批评话语分析（CDA）+ 语料库方法",
        "theorist_and_year": "Fairclough, 1989（CDA 原版提出者）；本篇为方法论研究",
        "core_content": "CDA 长期以定性研究为主，拘泥于单个文本的解读。语料库语言学定量研究与 CDA 定性研究有机结合，可提供数据基础，减少研究者偏见。Stubbs、Widdowson 等的代表性质疑推动了基于语料库的 CDA 新模式。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-106",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论6-Jerome Bruner-支架+STEM-1976.pdf",
        "original_filename": "理论6-Jerome Bruner-支架+STEM-1976.pdf",
        "title": "大数据时代在线学习者情感挖掘与干预研究（STEM+支架视角）",
        "authors": ["（待补，作者名 GBK 编码乱码）"],
        "source_journal": "现代远距离教育",
        "year": 2019,
        "issue": "3",
        "pages": "（总第183期）",
        "theory_tags": ["scaffolding", "STEM", "emotion_mining", "Bruner"],
        "theory_name": "支架式教学 + STEM 教育",
        "theorist_and_year": "Jerome Bruner, 1976（支架理论原版提出者）；本篇为 STEM 教育应用",
        "core_content": "大数据时代在线学习者情感挖掘与干预研究。涉及教育部人文社科青年基金、东北师范大学教师教育研究基金、吉林省十三五社科规划基金。",
        "_pending_verification": True,
        "_verification_note": "PDF 为 GBK-EUC-H 编码，作者名乱码；期刊名、年份、期号、主题已确认，作者与完整标题需在服务器用 PyMuPDF 验证。",
    },
    {
        "doc_id": "T-107",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论7-Jerome Bruner-支架-1976.pdf",
        "original_filename": "理论7-Jerome Bruner-支架-1976.pdf",
        "title": "支架式教学理论与实践",
        "authors": ["（待补，作者名 GBK 编码乱码）"],
        "source_journal": "中国职业技术教育",
        "year": 2015,
        "issue": "11",
        "theory_tags": ["scaffolding", "constructivism", "Bruner"],
        "theory_name": "支架式教学",
        "theorist_and_year": "布鲁纳、伍德等学者首次提出（原版）；1996年北京师范大学张建伟、陈琦教授首次介绍到中国",
        "core_content": "随着教学理论的发展，强调教师引起、维持、促进学生学习的建构主义教学观受到重视。支架式教学源自建筑业概念，指为学习者建构知识提供一种概念框架。20世纪90年代末伴随建构主义被介绍到中国。",
        "_pending_verification": True,
        "_verification_note": "PDF 为 GBK-EUC-H 编码；期刊名、年份、期号、主题已确认，作者与完整标题需在服务器用 PyMuPDF 验证。",
    },
    {
        "doc_id": "T-108",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论8-Vygotsky-社会文化理论-1922.pdf",
        "original_filename": "理论8-Vygotsky-社会文化理论-1922.pdf",
        "title": "Vygotsky 心理理论对二语教学的启发",
        "authors": ["张立新"],
        "source_journal": "中国海洋大学学报（社会科学版）",
        "year": 2006,
        "issue": "6",
        "theory_tags": ["sociocultural", "Vygotsky", "ZPD", "scaffolding", "internalization"],
        "theory_name": "社会文化理论（Sociocultural Theory）",
        "theorist_and_year": "Vygotsky, 20世纪30年代（原版提出者，非1922）；本篇为外语教学应用研究",
        "core_content": "社会文化理论强调中介作用与心理工具。最近发展区是重要概念，区分自发发展与系统教学。外语习得与母语习得的区别在于中介作用的对象（word meaning）。",
        "_pending_verification": True,
        "_verification_note": "PDF 为 GBK-EUC-H 编码；期刊名、年份、期号、主题已确认，完整标题与作者需在服务器用 PyMuPDF 验证。注意：文件名标的 1922 是 Vygotsky 实际工作时期，但理论原文发表年份更晚。",
    },
    {
        "doc_id": "T-109",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论9-最近发展区，支架理论.pdf",
        "original_filename": "理论9-最近发展区，支架理论.pdf",
        "title": "最近发展区中的词块习得实证研究——基于支架式教学的实验报告",
        "authors": ["盖淑华"],
        "source_journal": "（待补，作者单位：北京外国语大学中国外语教育研究中心 + 装甲兵工程学院）",
        "year": None,
        "theory_tags": ["ZPD", "scaffolding", "lexical_chunks", "Vygotsky"],
        "theory_name": "最近发展区理论 + 支架式教学",
        "theorist_and_year": "Vygotsky 最近发展区理论 + 支架式教学（实证研究报告）",
        "core_content": "以 Vygotsky 最近发展区理论为指导，通过为期一年的教学实验，采用支架式词块教学方法，探讨二语词块习得能力及其与语言能力的关系。71名非英语专业大学生参加实验。词块习得能力对写作能力提高起直接作用。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-110",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论10-董玉琦-CTCL 研究范式-2010.pdf",
        "original_filename": "理论10-董玉琦-CTCL 研究范式-2010.pdf",
        "title": "促进偏差认知转变的教学策略构建与应用研究",
        "authors": ["王靖", "董玉琦"],
        "source_journal": "电化教育研究",
        "year": 2016,
        "issue": "12",
        "pages": "（总第284期）",
        "theory_tags": ["CTCL", "biased_cognition", "educational_technology"],
        "theory_name": "CTCL 研究范式（Culture-Technology-Content-Learning）",
        "theorist_and_year": "董玉琦, 2010（CTCL 范式原版提出者）；本篇为应用研究（2016年）",
        "core_content": "依据 CTCL 研究范式，针对高中信息技术学科五个学习单元，依据学生偏差认知形成机制，设计转变学生偏差认知的教学策略，并检验其转变效果。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-111",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论11-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "original_filename": "理论11-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "title": "“产出导向法”在对外汉语教学中的应用：产出目标达成性考察",
        "authors": ["朱勇", "白雪"],
        "source_journal": "（待补，作者单位：北京外国语大学中文学院）",
        "year": None,
        "theory_tags": ["POA", "production_oriented", "文秋芳", "TSCA"],
        "theory_name": "产出导向法（Production-Oriented Approach, POA）",
        "theorist_and_year": "文秋芳, 2015（POA 实际提出者）；本篇为对外汉语教学应用研究。注意：文件名标为“弗雷德里克·泰勒-20世纪初”是事实性错误，POA 实际由文秋芳 2015 年提出。",
        "core_content": "基于 POA 教学材料使用与评价理论框架，考察 POA 教学实施后产出目标的达成性。通过对 50 名在华为来西亚大二留学生产出文本的分析，以及对任课教师和部分学生的深度访谈，发现 POA 汉语教学的产出目标达成效果较好。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-112",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论12-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "original_filename": "理论12-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "title": "“产出导向法”在对外汉语教学中的应用：教材改编",
        "authors": ["桂靖", "季陶"],
        "source_journal": "（待补，作者单位：北京外国语大学中文学院）",
        "year": None,
        "theory_tags": ["POA", "textbook_adaptation", "文秋芳"],
        "theory_name": "产出导向法（POA）- 教材改编应用",
        "theorist_and_year": "文秋芳, 2015（POA 提出者）；本篇为教材改编应用研究。注意：文件名标“泰勒-20世纪初”是事实性错误。",
        "core_content": "团队借鉴 POA 理论指导下大学英语教材《新一代》的编写经验，对汉语综合教材中的一课进行了 POA 化处理，并在对外汉语课堂进行了 4 课时实验。聚焦教材改编环节，从单元结构、生词、语言点以及练习设计等方面讨论改编过程。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-113",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论13-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "original_filename": "理论13-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "title": "基于 CiteSpace 的产出导向法在对外汉语教学中的可视化分析",
        "authors": ["（待补）"],
        "source_journal": "国际中文教育",
        "year": 2024,
        "issue": "18",
        "pages": "98-（总第367期）",
        "theory_tags": ["POA", "CiteSpace", "bibliometric", "对外汉语"],
        "theory_name": "产出导向法（POA）- 文献计量分析",
        "theorist_and_year": "文秋芳, 2015（POA 提出者）；2017年5月文秋芳及团队在首届创新外语教育在中国国际论坛上交流。本篇为可视化分析。注意：文件名标“泰勒-20世纪初”是事实性错误。",
        "core_content": "以中国知网、万方和维普三个数据库为研究对象，基于主题“产出导向法”并含“对外汉语教学”，对 2016-2023 年间相关文献进行可视化分析。研究主题主要有教学设计、线上教学、口语教学、驱动环节等，研究前沿转变为行动研究、偏误分析等。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-114",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论14-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "original_filename": "理论14-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "title": "“产出导向法”促成环节设计标准例析",
        "authors": ["邱琳"],
        "source_journal": "外语教育研究前沿",
        "year": 2020,
        "issue": "2",
        "volume": "3",
        "pages": "12-19",
        "theory_tags": ["POA", "facilitation", "precision", "progression", "diversity"],
        "theory_name": "产出导向法（POA）- 促成环节设计",
        "theorist_and_year": "文秋芳, 2015（POA 提出者，2018a 为引用版本）；本篇为促成环节设计研究。注意：文件名标“泰勒-20世纪初”是事实性错误。",
        "core_content": "促成有效性三大标准：精准性、渐进性、多样性。展示如何应用这些标准。促成不等同于课后练习，也不等同于几个活动的简单叠加。学用一体：学生学一点用一点，边学边用，输入与输出对接。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-115",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论15-文秋芳-师生合作评价-2016.pdf",
        "original_filename": "理论15-文秋芳-师生合作评价-2016.pdf",
        "title": "“师生合作评价”：“产出导向法”创设的新评价形式",
        "authors": ["文秋芳"],
        "source_journal": "（待补，从内容看是 2016 年发表）",
        "year": 2016,
        "theory_tags": ["TSCA", "POA", "assessment", "文秋芳"],
        "theory_name": "师生合作评价（Teacher-Student Collaborative Assessment, TSCA）",
        "theorist_and_year": "文秋芳, 2016（TSCA 提出者）；POA 评价环节的核心创新",
        "core_content": "POA 始于产出、止于产出，特别重视对学生产出结果的有效评价。我国大学英语班级大、教师工作负担重，对每个产出任务给予及时有效评价是极大挑战。TSCA 是 POA 提出的新评价设想，以组织、平衡教师评价与其他评价方式。包括课前、课内和课后 3 个阶段。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-116",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论16-文秋芳-师生合作评价-2016.pdf",
        "original_filename": "理论16-文秋芳-师生合作评价-2016.pdf",
        "title": "师生合作评价（TSCA）在 POA 单元产品评价中的应用",
        "authors": ["（待补，从内容看作者非文秋芳本人，是 TSCA 应用研究者）"],
        "source_journal": "现代外语",
        "year": 2017,
        "issue": "3",
        "volume": "40",
        "theory_tags": ["TSCA", "POA", "application_research"],
        "theory_name": "师生合作评价（TSCA）- 应用研究",
        "theorist_and_year": "文秋芳, 2016（TSCA 提出者）；本篇为应用研究。基金项目：教育部人文社科重点研究基地重大项目 16JJD740002 子课题",
        "core_content": "TSCA 是 POA 团队提出的新评价形式，旨在解决评价效率低和效果差的问题。课前教师对典型样本进行详批，课内学生之间合作、教师与学生合作共同评价。本研究在一所211大学英语专业二年级开展，24 名学生，研究历时 16 周。",
        "_pending_verification": False,
    },
    {
        "doc_id": "T-117",
        "file_path": "C:/Users/ht/Documents/outeye3.0/seed-materials/数据收集0811/教学理论/理论17-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "original_filename": "理论17-弗雷德里克·泰勒-产出导向法-20世纪初.pdf",
        "title": "“产出导向法”中师生合作评价原则例析",
        "authors": ["孙曙光"],
        "source_journal": "外语教育研究前沿",
        "year": 2020,
        "issue": "2",
        "volume": "3",
        "pages": "20-27",
        "theory_tags": ["TSCA", "POA", "principles", "孙曙光"],
        "theory_name": "师生合作评价（TSCA）- 实施原则",
        "theorist_and_year": "孙曙光, 2020（实施原则提出者）；TSCA 原型由文秋芳 2016 提出。注意：文件名标“泰勒-20世纪初”是事实性错误。",
        "core_content": "TSCA 实施原则：课前目标导向、重点突出，课中问题驱动、支架渐进，课后过程监控、推优示范。通过辩证研究（文秋芳 2018a）摸索出 POA 中应用 TSCA 的实施原则。以一个单元案例解析评价的具体实施。",
        "_pending_verification": False,
    },
]


def main():
    if not DOCX_PATH.exists():
        print(f"ERROR: docx not found: {DOCX_PATH}", file=sys.stderr)
        sys.exit(1)

    entries_0729 = extract_0729_theory_from_docx()
    # 给 0811 标 batch=core，0729 标 batch=supplementary
    for e in entries_0729:
        e["batch"] = "supplementary"
        e["source_pdf_dir"] = "0729"
    for e in THEORY_0811:
        e["batch"] = "core"
        e["source_pdf_dir"] = "0811"

    all_entries = entries_0729 + THEORY_0811

    manifest = {
        "schema_version": "1.0",
        "generated_at": None,  # 填入时戳
        "total_count": len(all_entries),
        "batches": {
            "core": "0811 教学理论目录 17 篇核心论文",
            "supplementary": "0729 理论目录 10 篇补充论文",
        },
        "entries": all_entries,
        "notes": [
            "doc_id 编号规则：core 批次 T-101~T-117（0811 目录原文件名序号），supplementary 批次 T-001~T-010（0729 目录 docx 顺序）",
            "0811 目录的 PDF 文件名（如“理论11-弗雷德里克·泰勒-产出导向法-20世纪初.pdf”）只是理论标签，实际内容是引用该理论的中文论文，真实作者/标题/年份以本清单为准",
            "标注 _pending_verification=true 的条目为 PyPDF2 解析乱码（GBK-EUC-H 编码），现有元数据从乱码中可识别字符推断，需在服务器装 PyMuPDF 后重新解析验证",
            "0811 目录中“弗雷德里克·泰勒-产出导向法-20世纪初”是事实性错误：POA 实际由文秋芳 2015 年提出，不是泰勒",
            "Vygotsky 社会文化理论实际提出于 20世纪30年代，文件名标 1922 是误导性标记",
            "scope 字段在 seed 脚本写入时统一为 system，owner_id 为 null",
        ],
    }

    from datetime import datetime, timezone
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"OK: {len(all_entries)} entries written to {OUTPUT_PATH}")
    print(f"  - core (0811): {len([e for e in all_entries if e['batch'] == 'core'])}")
    print(f"  - supplementary (0729): {len([e for e in all_entries if e['batch'] == 'supplementary'])}")
    print(f"  - pending_verification: {len([e for e in all_entries if e.get('_pending_verification')])}")


if __name__ == "__main__":
    main()
