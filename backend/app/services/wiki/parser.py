"""
Wiki文件解析器
解析Markdown格式的Wiki文件，提取结构化信息
"""

import re
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


@dataclass
class WikiFrontmatter:
    """Wiki页面前置元数据"""
    title: str
    created: str
    updated: str
    type: str
    tags: List[str]
    sources: List[str]
    confidence: str
    contested: bool
    contradictions: List[str]


@dataclass
class WikiPage:
    """Wiki页面结构"""
    path: str
    filename: str
    frontmatter: WikiFrontmatter
    content: str
    sections: Dict[str, str]
    wikilinks: List[str]
    backlinks: List[str]


class WikiParser:
    """Wiki文件解析器"""

    def __init__(self, wiki_root: str):
        """
        初始化解析器

        Args:
            wiki_root: Wiki根目录路径
        """
        self.wiki_root = Path(wiki_root)
        self.pages: Dict[str, WikiPage] = {}
        self.index: Dict[str, List[str]] = {}  # 标签到页面的索引

    def parse_all(self) -> Dict[str, WikiPage]:
        """解析所有Wiki文件"""
        self.pages.clear()
        self.index.clear()

        # 遍历所有Markdown文件
        for md_file in self.wiki_root.rglob("*.md"):
            if md_file.name.startswith("."):
                continue

            try:
                page = self.parse_file(md_file)
                if page:
                    self.pages[page.filename] = page
                    self._index_page(page)
            except Exception as e:
                print(f"Error parsing {md_file}: {e}")

        # 建立反向链接
        self._build_backlinks()

        return self.pages

    def parse_file(self, file_path: Path) -> Optional[WikiPage]:
        """
        解析单个Wiki文件

        Args:
            file_path: 文件路径

        Returns:
            WikiPage对象或None
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

        # 解析前置元数据
        frontmatter = self._parse_frontmatter(content)

        # 提取内容（去掉前置元数据）
        main_content = self._extract_main_content(content)

        # 解析章节
        sections = self._parse_sections(main_content)

        # 提取wikilinks
        wikilinks = self._extract_wikilinks(main_content)

        # 计算相对路径
        relative_path = file_path.relative_to(self.wiki_root)

        return WikiPage(
            path=str(relative_path),
            filename=file_path.stem,
            frontmatter=frontmatter,
            content=main_content,
            sections=sections,
            wikilinks=wikilinks,
            backlinks=[]  # 稍后填充
        )

    def _parse_frontmatter(self, content: str) -> WikiFrontmatter:
        """解析YAML前置元数据"""
        # 匹配 --- 之间的内容
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)

        if match:
            yaml_content = match.group(1)
            try:
                data = yaml.safe_load(yaml_content)
            except yaml.YAMLError:
                data = {}
        else:
            data = {}

        return WikiFrontmatter(
            title=data.get('title', ''),
            created=data.get('created', ''),
            updated=data.get('updated', ''),
            type=data.get('type', ''),
            tags=data.get('tags', []),
            sources=data.get('sources', []),
            confidence=data.get('confidence', 'medium'),
            contested=data.get('contested', False),
            contradictions=data.get('contradictions', [])
        )

    def _extract_main_content(self, content: str) -> str:
        """提取主要内容（去掉前置元数据）"""
        pattern = r'^---\s*\n.*?\n---\s*\n'
        return re.sub(pattern, '', content, flags=re.DOTALL).strip()

    def _parse_sections(self, content: str) -> Dict[str, str]:
        """解析章节结构"""
        sections = {}
        current_section = "introduction"
        current_content = []

        for line in content.split('\n'):
            # 检查是否是标题
            if line.startswith('#'):
                # 保存之前的章节
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()

                # 开始新章节
                current_section = line.lstrip('#').strip()
                current_content = []
            else:
                current_content.append(line)

        # 保存最后一个章节
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def _extract_wikilinks(self, content: str) -> List[str]:
        """提取wikilinks"""
        # 匹配 [[link]] 或 [[link|display]]
        pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
        matches = re.findall(pattern, content)
        return list(set(matches))

    def _index_page(self, page: WikiPage):
        """为页面建立索引"""
        # 按标签索引
        for tag in page.frontmatter.tags:
            if tag not in self.index:
                self.index[tag] = []
            self.index[tag].append(page.filename)

        # 按类型索引
        page_type = page.frontmatter.type
        if page_type:
            type_key = f"type:{page_type}"
            if type_key not in self.index:
                self.index[type_key] = []
            self.index[type_key].append(page.filename)

    def _build_backlinks(self):
        """建立反向链接"""
        # 清空现有反向链接
        for page in self.pages.values():
            page.backlinks = []

        # 建立反向链接映射
        for page in self.pages.values():
            for link in page.wikilinks:
                if link in self.pages:
                    self.pages[link].backlinks.append(page.filename)

    def get_page(self, filename: str) -> Optional[WikiPage]:
        """获取页面"""
        return self.pages.get(filename)

    def search_by_tag(self, tag: str) -> List[WikiPage]:
        """按标签搜索页面"""
        page_names = self.index.get(tag, [])
        return [self.pages[name] for name in page_names if name in self.pages]

    def search_by_type(self, page_type: str) -> List[WikiPage]:
        """按类型搜索页面"""
        type_key = f"type:{page_type}"
        page_names = self.index.get(type_key, [])
        return [self.pages[name] for name in page_names if name in self.pages]

    def search_by_keyword(self, keyword: str) -> List[WikiPage]:
        """按关键词搜索页面"""
        results = []
        keyword_lower = keyword.lower()

        for page in self.pages.values():
            # 搜索标题
            if keyword_lower in page.frontmatter.title.lower():
                results.append(page)
                continue

            # 搜索内容
            if keyword_lower in page.content.lower():
                results.append(page)
                continue

            # 搜索标签
            if any(keyword_lower in tag.lower() for tag in page.frontmatter.tags):
                results.append(page)
                continue

        return results

    def get_related_pages(self, filename: str) -> List[WikiPage]:
        """获取相关页面（通过wikilinks）"""
        page = self.get_page(filename)
        if not page:
            return []

        related = []
        for link in page.wikilinks:
            if link in self.pages:
                related.append(self.pages[link])

        return related

    def get_backlinks(self, filename: str) -> List[WikiPage]:
        """获取反向链接页面"""
        page = self.get_page(filename)
        if not page:
            return []

        return [self.pages[bl] for bl in page.backlinks if bl in self.pages]

    # 元数据标签前缀，不是用户可见的理论标签
    _META_TAG_PREFIXES = ("concept-layer:", "type:", "theory-layer:", "source:", "function:")

    def get_all_tags(self) -> List[str]:
        """获取所有标签（过滤掉元数据标签）"""
        return [
            tag for tag in self.index.keys()
            if not any(tag.startswith(prefix) for prefix in self._META_TAG_PREFIXES)
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_pages": len(self.pages),
            "total_tags": len(self.index),
            "page_types": {
                page_type: len(self.search_by_type(page_type))
                for page_type in set(p.frontmatter.type for p in self.pages.values() if p.frontmatter.type)
            },
            "pages_with_backlinks": sum(1 for p in self.pages.values() if p.backlinks),
            "average_wikilinks": sum(len(p.wikilinks) for p in self.pages.values()) / max(len(self.pages), 1)
        }