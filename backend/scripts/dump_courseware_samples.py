"""只读导出课件 HTML 样本，供 V2 编辑器 benchmark 使用。

用法:
  venv/Scripts/python.exe scripts/dump_courseware_samples.py [--out DIR] [--max N] [--count-only]

- 每个项目只取最新一个带 rendered_html 的版本
- 输出 <out>/sample-<seq>.html + manifest.json（项目标题/字节数/来源标记）
"""
import argparse
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings  # noqa: E402


def to_asyncpg_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join("..", "..", "frontend", "scripts", "v2benchmark", "samples"))
    parser.add_argument("--max", type=int, default=100)
    parser.add_argument("--count-only", action="store_true")
    args = parser.parse_args()

    import asyncpg

    conn = await asyncpg.connect(to_asyncpg_dsn(settings.DATABASE_URL))
    try:
        rows = await conn.fetch(
            """
            SELECT p.id AS project_id, p.title, p.source_type, p.source_meta,
                   v.id AS version_id, v.version_number, v.rendered_html, v.created_at
            FROM courseware_versions v
            JOIN courseware_projects p ON p.id = v.project_id
            WHERE v.rendered_html IS NOT NULL AND length(v.rendered_html) > 1500
            ORDER BY v.created_at DESC
            """
        )
        latest = {}
        for r in rows:
            if r["project_id"] not in latest:
                latest[r["project_id"]] = r
        items = list(latest.values())
        print(f"带 rendered_html(>1500) 的项目数: {len(items)}（版本总数 {len(rows)}）")
        if args.count_only:
            return

        out_dir = os.path.abspath(args.out)
        os.makedirs(out_dir, exist_ok=True)
        manifest = []
        for i, r in enumerate(items[: args.max], 1):
            name = f"sample-{i:02d}.html"
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
                f.write(r["rendered_html"])
            meta = r["source_meta"] or {}
            manifest.append(
                {
                    "file": name,
                    "project_id": r["project_id"],
                    "version_id": r["version_id"],
                    "title": r["title"],
                    "source_type": r["source_type"],
                    "source_meta": meta,
                    "bytes": len(r["rendered_html"].encode("utf-8")),
                    "has_llm_marker": bool(re.search(r"data-ve-component|ve-component|data-component", r["rendered_html"])),
                }
            )
        with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"已导出 {len(manifest)} 个样本到 {out_dir}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
