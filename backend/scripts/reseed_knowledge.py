"""
重新播种系统知识种子

删除 Qdrant 中所有 scope=system 的 points，然后重新播种 5 篇匿名化系统知识
（带 doc_type / tags / created_at）。

用法（在 backend 目录下执行）：
    python scripts/reseed_knowledge.py

注意：
- 会加载 Embedding 模型（约需 60 秒）
- 只删除 scope=system 的 points，不影响用户 private 数据
"""

import os
import sys
from pathlib import Path

# 服务器无法访问 huggingface.co，强制离线模式，避免加载模型时联网校验失败
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# 让脚本可直接执行，无需手动设置 PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    from app.api.api_v1.endpoints.rag import get_rag_services
    from app.services.knowledge_seed import seed_system_knowledge
    from app.core.scope import SCOPE_SYSTEM

    print("加载 RAG 服务（含 Embedding 模型，约 60 秒）...")
    services = get_rag_services()
    vector_store = services["vector_store"]
    embedding = services["embedding"]

    print("清理 Qdrant 中 scope=system 的 points ...")
    records = vector_store.get_all_records()
    system_ids = [r.id for r in records if (r.payload or {}).get("scope") == SCOPE_SYSTEM]
    if system_ids:
        vector_store.delete(system_ids)
    print(f"已删除 {len(system_ids)} 个 system points")

    print("重新播种系统知识 ...")
    result = seed_system_knowledge(vector_store, embedding)
    print(f"播种结果: {result}")

    # 验证
    records = vector_store.get_all_records()
    seeded = [r for r in records if (r.payload or {}).get("scope") == SCOPE_SYSTEM]
    print(f"\n验证：当前 system 文档 {len(seeded)} 个 points")
    titles = sorted({(r.payload or {}).get("title", "") for r in seeded})
    for t in titles:
        print(f"  - {t}")


if __name__ == "__main__":
    main()
