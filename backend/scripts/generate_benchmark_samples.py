"""零 token 生成 benchmark 样本（bootstrap 课件 HTML）。

用 demo 教案 × slides/longform 两种模式生成确定性样本，
并收录既有的 LLM 实链测试课件与课堂模板作为结构多样性来源。

用法:
  venv/Scripts/python.exe scripts/generate_benchmark_samples.py [--out DIR]
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.courseware_bootstrap import build_courseware_from_plan  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_demo_plans():
    plans = []
    for i in (1, 2, 3):
        p = os.path.join(BACKEND_DIR, f"demo_lesson_plan_{i}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                plans.append(json.load(f))
    return plans


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=os.path.join(BACKEND_DIR, "..", "frontend", "scripts", "v2benchmark", "samples"),
    )
    args = parser.parse_args()
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    manifest = []
    for i, plan in enumerate(load_demo_plans(), 1):
        for mode in ("slides", "longform"):
            payload = build_courseware_from_plan(
                title=f"Benchmark Demo {i}",
                mode=mode,
                template_id="classroom_default",
                plan=plan,
            )
            name = f"bootstrap-{i:02d}-{mode}.html"
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
                f.write(payload["rendered_html"])
            manifest.append({"file": name, "kind": "bootstrap", "mode": mode})

    extras = [
        (os.path.join(BACKEND_DIR, "regression_runs", "courseware_html_test.html"), "llm-real"),
        (os.path.join(BACKEND_DIR, "templates", "html", "classroom_default.html"), "template"),
    ]
    for src, kind in extras:
        if os.path.exists(src):
            name = f"{kind}-{os.path.basename(src)}"
            shutil.copyfile(src, os.path.join(out_dir, name))
            manifest.append({"file": name, "kind": kind})

    with open(os.path.join(out_dir, "bootstrap-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"已生成 {len(manifest)} 个零 token 样本 -> {out_dir}")


if __name__ == "__main__":
    main()
