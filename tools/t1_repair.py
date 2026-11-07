#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T1 校验闭环：校验 LLM 输出的 SIR；不通过则生成修复提示词。

用法：
    python tools/t1_repair.py --sir candidate.json
    python tools/t1_repair.py --sir candidate.json --out repair_prompt.md

退出码：0=通过；1=不通过（并写出修复提示词）。
"""

import json
import os
import sys
import subprocess
import argparse
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tools", "check.py")
PY = sys.executable


def main():
    ap = argparse.ArgumentParser(description="T1 校验闭环")
    ap.add_argument("--sir", required=True)
    ap.add_argument("--out", default="t1_repair_prompt.md")
    args = ap.parse_args()

    fd, log = tempfile.mkstemp(suffix=".json", prefix="t1check_")
    os.close(fd)
    try:
        with open(log, "w", encoding="utf-8") as f:
            subprocess.run([PY, CHECK, "sir", args.sir], stdout=f, stderr=subprocess.STDOUT)
        with open(log, "r", encoding="utf-8") as f:
            txt = f.read().strip()
        report = json.loads(txt) if txt.startswith("{") else {"ok": False, "errors": ["校验器输出无法解析"]}
    finally:
        try:
            os.remove(log)
        except OSError:
            pass

    if report.get("ok"):
        print(json.dumps({"ok": True, "note": "SIR 校验通过，可进入 T2/T3"}, ensure_ascii=False, indent=2))
        return 0

    errors = report.get("errors", [])
    with open(args.sir, "r", encoding="utf-8") as f:
        candidate = f.read().strip()

    repair = (
        "上次输出未通过 SIR 校验，错误如下：\n"
        + "\n".join(f"- {e}" for e in errors)
        + "\n\n要求：\n"
        "1. 只修正错误，保留其余内容；\n"
        "2. 不要新增输入中没有的事实；\n"
        "3. 不确定的字段写 unknown 并放入 unknowns；\n"
        "4. 重新输出完整 JSON（不要只输出修改片段），不要 Markdown 代码块。\n\n"
        "原始输出：\n```json\n" + candidate + "\n```\n"
    )
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(repair)

    print(json.dumps({
        "ok": False,
        "error_count": len(errors),
        "errors": errors,
        "repair_prompt": os.path.abspath(args.out),
        "note": "把 repair_prompt 交给 LLM 重新输出，最多重试 2 次",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    sys.exit(main())
