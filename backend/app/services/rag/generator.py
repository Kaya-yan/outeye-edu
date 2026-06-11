"""
RAG生成器

实现基于检索结果的回答生成
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import time


@dataclass
class GenerationResult:
    """生成结果"""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    response_time: float
    model: str
    usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """检索结果"""
    chunk_id: str
    doc_id: str
    content: str
    score: float
    retrieval_method: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGGenerator:
    """RAG生成器"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = "deepseek-chat",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p

        # 初始化客户端
        self._init_client()

    def _init_client(self):
        """初始化LLM客户端"""
        try:
            import openai

            self.client = openai.OpenAI(
                api_key=self.api_key or "dummy",
                base_url=self.api_base
            )
            self.use_api = True

        except ImportError:
            print("警告: openai未安装，将使用简化实现")
            self.client = None
            self.use_api = False

    def generate(
        self,
        query: str,
        retrieval_results: List[RetrievalResult],
        system_prompt: Optional[str] = None,
        include_sources: bool = True
    ) -> GenerationResult:
        """
        生成回答

        Args:
            query: 用户查询
            retrieval_results: 检索结果
            system_prompt: 系统提示
            include_sources: 是否包含来源

        Returns:
            生成结果
        """
        start_time = time.time()

        # 组装上下文
        context = self._assemble_context(retrieval_results)

        # 构建Prompt
        messages = self._build_messages(query, context, system_prompt)

        # 调用LLM
        if self.use_api:
            answer, usage = self._generate_with_api(messages)
        else:
            answer = self._generate_simplified(query, context)
            usage = {}

        # 计算置信度
        confidence = self._calculate_confidence(retrieval_results)

        # 构建来源信息
        sources = []
        if include_sources:
            sources = self._build_sources(retrieval_results)

        response_time = time.time() - start_time

        return GenerationResult(
            answer=answer,
            sources=sources,
            confidence=confidence,
            response_time=response_time,
            model=self.model,
            usage=usage
        )

    def _assemble_context(self, results: List[RetrievalResult]) -> str:
        """组装上下文"""
        if not results:
            return "没有找到相关文档。"

        context_parts = []
        for i, result in enumerate(results, 1):
            source_info = f"[文档{i}]"
            if result.metadata.get('title'):
                source_info += f" 来源: {result.metadata['title']}"
            if result.metadata.get('source'):
                source_info += f" ({result.metadata['source']})"

            context_parts.append(
                f"{source_info}\n{result.content}\n相关度: {result.score:.2f}"
            )

        return "\n\n".join(context_parts)

    def _build_messages(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str]
    ) -> List[Dict[str, str]]:
        """构建消息"""
        messages = []

        # 系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system",
                "content": """你是一位专业的教学助手，专注于语言学和教育领域。
请基于提供的文档内容回答用户的问题。

回答要求：
1. 基于文档内容回答，不要编造信息
2. 如果文档中没有相关信息，请明确说明
3. 引用相关文档编号作为依据
4. 回答要准确、专业、有条理
5. 使用中文回答"""
            })

        # 用户消息
        user_message = f"""请基于以下文档内容回答问题。

检索到的文档：
{context}

用户问题：{query}"""

        messages.append({"role": "user", "content": user_message})

        return messages

    def _generate_with_api(self, messages: List[Dict[str, str]]) -> tuple:
        """使用API生成"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p
            )

            answer = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

            return answer, usage

        except Exception as e:
            print(f"API调用失败: {e}")
            return self._generate_simplified(
                messages[-1]["content"],
                ""
            ), {}

    def _generate_simplified(self, query: str, context: str) -> str:
        """简化生成"""
        # 提取关键信息
        if "没有找到相关文档" in context:
            return f"抱歉，没有找到与《{query}》相关的文档。请尝试换个方式提问，或者提供更多上下文信息。"

        # 简单的模板回答
        answer = f"根据检索到的文档，关于《{query}》的信息如下：\n\n"

        # 从上下文中提取关键句子
        sentences = context.split('。')
        relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 10][:5]

        for i, sentence in enumerate(relevant_sentences, 1):
            answer += f"{i}. {sentence}。\n"

        answer += "\n以上信息来自检索到的文档，建议进一步查阅原始资料获取更详细的内容。"

        return answer

    def _calculate_confidence(self, results: List[RetrievalResult]) -> float:
        """计算置信度"""
        if not results:
            return 0.0

        # 基于检索结果的平均分数
        avg_score = sum(r.score for r in results) / len(results)

        # 基于结果数量
        count_factor = min(len(results) / 5, 1.0)

        # 综合置信度
        confidence = avg_score * 0.7 + count_factor * 0.3

        return min(confidence, 1.0)

    def _build_sources(self, results: List[RetrievalResult]) -> List[Dict[str, Any]]:
        """构建来源信息"""
        sources = []

        for i, result in enumerate(results, 1):
            source = {
                "index": i,
                "chunk_id": result.chunk_id,
                "doc_id": result.doc_id,
                "score": result.score,
                "method": result.retrieval_method,
                "excerpt": result.content[:200] + "..." if len(result.content) > 200 else result.content
            }

            # 添加元数据
            if result.metadata.get('title'):
                source['title'] = result.metadata['title']
            if result.metadata.get('source'):
                source['source'] = result.metadata['source']

            sources.append(source)

        return sources

    def generate_with_wiki(
        self,
        query: str,
        wiki_results: List[Dict],
        rag_results: List[RetrievalResult],
        system_prompt: Optional[str] = None
    ) -> GenerationResult:
        """
        结合Wiki和RAG结果生成回答

        Args:
            query: 用户查询
            wiki_results: Wiki查询结果
            rag_results: RAG检索结果
            system_prompt: 系统提示

        Returns:
            生成结果
        """
        start_time = time.time()

        # 组装Wiki上下文
        wiki_context = self._assemble_wiki_context(wiki_results)

        # 组装RAG上下文
        rag_context = self._assemble_context(rag_results)

        # 构建综合上下文
        full_context = ""
        if wiki_context:
            full_context += f"=== Wiki知识库 ===\n{wiki_context}\n\n"
        if rag_context:
            full_context += f"=== 检索文档 ===\n{rag_context}"

        # 构建消息
        messages = self._build_messages(query, full_context, system_prompt)

        # 生成
        if self.use_api:
            answer, usage = self._generate_with_api(messages)
        else:
            answer = self._generate_simplified(query, full_context)
            usage = {}

        # 计算置信度
        confidence = self._calculate_combined_confidence(wiki_results, rag_results)

        # 构建来源
        sources = []
        if wiki_results:
            sources.append({
                "type": "wiki",
                "count": len(wiki_results),
                "items": wiki_results[:3]
            })
        if rag_results:
            sources.append({
                "type": "document",
                "count": len(rag_results),
                "items": self._build_sources(rag_results)[:3]
            })

        response_time = time.time() - start_time

        return GenerationResult(
            answer=answer,
            sources=sources,
            confidence=confidence,
            response_time=response_time,
            model=self.model,
            usage=usage
        )

    def _assemble_wiki_context(self, wiki_results: List[Dict]) -> str:
        """组装Wiki上下文"""
        if not wiki_results:
            return ""

        context_parts = []
        for i, result in enumerate(wiki_results, 1):
            title = result.title if hasattr(result, 'title') else result.get('title', f'Wiki条目{i}')
            content = result.content if hasattr(result, 'content') else result.get('content', '')

            # 截取内容
            if len(content) > 500:
                content = content[:500] + "..."

            context_parts.append(f"[Wiki {i}] {title}\n{content}")

        return "\n\n".join(context_parts)

    def _calculate_combined_confidence(
        self,
        wiki_results: List[Dict],
        rag_results: List[RetrievalResult]
    ) -> float:
        """计算综合置信度"""
        wiki_confidence = 0.0
        rag_confidence = 0.0

        # Wiki置信度
        if wiki_results:
            wiki_confidence = 0.8  # Wiki通常更可靠

        # RAG置信度
        if rag_results:
            rag_confidence = self._calculate_confidence(rag_results)

        # 综合置信度
        if wiki_results and rag_results:
            return max(wiki_confidence, rag_confidence)
        elif wiki_results:
            return wiki_confidence
        elif rag_results:
            return rag_confidence
        else:
            return 0.0
