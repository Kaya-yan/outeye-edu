"""
Wiki查询服务
提供高级查询功能，支持理论检索、知识图谱查询等
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .parser import WikiParser, WikiPage


@dataclass
class QueryResult:
    """查询结果"""
    page: WikiPage
    relevance_score: float
    match_type: str  # exact, partial, related
    matched_sections: List[str]


class WikiQuery:
    """Wiki查询服务"""

    def __init__(self, wiki_root: str):
        """
        初始化查询服务

        Args:
            wiki_root: Wiki根目录路径
        """
        self.parser = WikiParser(wiki_root)
        self.parser.parse_all()

    def query(self, query_text: str, max_results: int = 10) -> List[QueryResult]:
        """
        执行查询

        Args:
            query_text: 查询文本
            max_results: 最大结果数

        Returns:
            查询结果列表
        """
        results = []

        # 1. 精确匹配标题
        exact_matches = self._exact_title_match(query_text)
        results.extend(exact_matches)

        # 2. 关键词搜索
        keyword_matches = self._keyword_search(query_text)
        results.extend(keyword_matches)

        # 3. 标签搜索
        tag_matches = self._tag_search(query_text)
        results.extend(tag_matches)

        # 4. 内容搜索
        content_matches = self._content_search(query_text)
        results.extend(content_matches)

        # 去重并排序
        results = self._deduplicate_and_rank(results)

        return results[:max_results]

    def query_theory(self, theory_name: str) -> List[QueryResult]:
        """
        查询理论

        Args:
            theory_name: 理论名称

        Returns:
            相关理论页面
        """
        # 搜索理论实体页
        results = []

        # 精确匹配
        exact = self._exact_title_match(theory_name)
        results.extend(exact)

        # 搜索包含理论名称的页面
        for page in self.parser.pages.values():
            if theory_name.lower() in page.frontmatter.title.lower():
                results.append(QueryResult(
                    page=page,
                    relevance_score=0.9,
                    match_type="exact",
                    matched_sections=[page.frontmatter.title]
                ))

        # 搜索标签中包含理论的页面
        theory_tags = [tag for tag in self.parser.get_all_tags() if 'theory' in tag.lower()]
        for tag in theory_tags:
            for page in self.parser.search_by_tag(tag):
                if theory_name.lower() in page.content.lower():
                    results.append(QueryResult(
                        page=page,
                        relevance_score=0.7,
                        match_type="related",
                        matched_sections=self._find_matching_sections(page, theory_name)
                    ))

        return self._deduplicate_and_rank(results)

    def query_for_text_analysis(self, text_type: str, student_level: str) -> List[QueryResult]:
        """
        为课文分析查询相关理论

        Args:
            text_type: 课文类型（academic, literary, news等）
            student_level: 学生水平（A1-C2）

        Returns:
            相关理论和策略
        """
        results = []

        # 1. 查询难度评估理论
        if text_type == "academic":
            results.extend(self.query_theory("Lexile"))
            results.extend(self.query_theory("Flesch-Kincaid"))
            results.extend(self.query_theory("CEFR"))

        # 2. 查询二语习得理论
        results.extend(self.query_theory("Krashen"))
        results.extend(self.query_theory("i+1"))

        # 3. 查询认知负荷理论
        results.extend(self.query_theory("认知负荷"))

        # 4. 查询教学设计理论
        results.extend(self.query_theory("Bloom"))
        results.extend(self.query_theory("ZPD"))

        return self._deduplicate_and_rank(results)

    def query_for_lesson_plan(self, topic: str, objectives: List[str]) -> List[QueryResult]:
        """
        为教案生成查询相关理论

        Args:
            topic: 教学主题
            objectives: 教学目标

        Returns:
            相关理论和策略
        """
        results = []

        # 1. 查询教学设计理论
        results.extend(self.query_theory("Bloom"))
        results.extend(self.query_theory("教学设计"))

        # 2. 查询二语习得理论
        results.extend(self.query_theory("Krashen"))
        results.extend(self.query_theory("输入假说"))

        # 3. 查询认知理论
        results.extend(self.query_theory("认知负荷"))
        results.extend(self.query_theory("Noticing"))

        # 4. 查询与主题相关的理论
        topic_results = self.query(topic)
        results.extend(topic_results)

        return self._deduplicate_and_rank(results)

    def get_theory_network(self, theory_name: str) -> Dict[str, Any]:
        """
        获取理论网络（关联理论）

        Args:
            theory_name: 理论名称

        Returns:
            理论网络结构
        """
        # 查找理论页面
        theory_pages = self.query_theory(theory_name)
        if not theory_pages:
            return {"error": "Theory not found"}

        main_page = theory_pages[0].page

        # 获取关联理论
        related_theories = []
        for link in main_page.wikilinks:
            linked_page = self.parser.get_page(link)
            if linked_page:
                related_theories.append({
                    "name": linked_page.frontmatter.title,
                    "type": linked_page.frontmatter.type,
                    "relationship": "referenced"
                })

        # 获取反向引用
        backlinks = self.parser.get_backlinks(main_page.filename)
        for bl in backlinks:
            related_theories.append({
                "name": bl.frontmatter.title,
                "type": bl.frontmatter.type,
                "relationship": "references_this"
            })

        return {
            "main_theory": {
                "name": main_page.frontmatter.title,
                "tags": main_page.frontmatter.tags,
                "confidence": main_page.frontmatter.confidence
            },
            "related_theories": related_theories,
            "network_size": len(related_theories)
        }

    def _exact_title_match(self, query: str) -> List[QueryResult]:
        """精确标题匹配"""
        results = []
        query_lower = query.lower()

        for page in self.parser.pages.values():
            if query_lower == page.frontmatter.title.lower():
                results.append(QueryResult(
                    page=page,
                    relevance_score=1.0,
                    match_type="exact",
                    matched_sections=[page.frontmatter.title]
                ))

        return results

    def _keyword_search(self, query: str) -> List[QueryResult]:
        """关键词搜索"""
        results = []
        keywords = query.lower().split()

        for page in self.parser.pages.values():
            matched_sections = []

            # 检查标题
            if any(kw in page.frontmatter.title.lower() for kw in keywords):
                matched_sections.append(page.frontmatter.title)

            # 检查章节
            for section_name, section_content in page.sections.items():
                if any(kw in section_content.lower() for kw in keywords):
                    matched_sections.append(section_name)

            if matched_sections:
                # 计算相关性分数
                score = len(matched_sections) / (len(keywords) + 1)
                results.append(QueryResult(
                    page=page,
                    relevance_score=min(score, 0.9),
                    match_type="partial",
                    matched_sections=matched_sections
                ))

        return results

    def _tag_search(self, query: str) -> List[QueryResult]:
        """标签搜索"""
        results = []
        query_lower = query.lower()

        # 搜索匹配的标签
        matching_tags = [tag for tag in self.parser.get_all_tags() if query_lower in tag.lower()]

        for tag in matching_tags:
            for page in self.parser.search_by_tag(tag):
                results.append(QueryResult(
                    page=page,
                    relevance_score=0.8,
                    match_type="tag",
                    matched_sections=[f"tag: {tag}"]
                ))

        return results

    def _content_search(self, query: str) -> List[QueryResult]:
        """内容搜索"""
        results = []
        query_lower = query.lower()

        for page in self.parser.pages.values():
            if query_lower in page.content.lower():
                # 找到匹配的章节
                matched_sections = self._find_matching_sections(page, query)

                results.append(QueryResult(
                    page=page,
                    relevance_score=0.6,
                    match_type="content",
                    matched_sections=matched_sections
                ))

        return results

    def _find_matching_sections(self, page: WikiPage, query: str) -> List[str]:
        """找到匹配的章节"""
        matched = []
        query_lower = query.lower()

        for section_name, section_content in page.sections.items():
            if query_lower in section_content.lower():
                matched.append(section_name)

        return matched

    def _deduplicate_and_rank(self, results: List[QueryResult]) -> List[QueryResult]:
        """去重并排序"""
        # 按页面去重
        seen = {}
        for result in results:
            page_id = result.page.filename
            if page_id not in seen or result.relevance_score > seen[page_id].relevance_score:
                seen[page_id] = result

        # 按相关性排序
        sorted_results = sorted(seen.values(), key=lambda x: x.relevance_score, reverse=True)

        return sorted_results