#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T10 法律风险检查（规则版，标准库）

用法：
    python tools/t10_legal.py --text "我打算曝光他的隐私，威胁他"
    python tools/t10_legal.py --text "向熟人打听对方性格" --checkpoint C2

输出：legal_risks[] + blocked；存在 red 时退出码 1。默认中国法域，不构成法律意见。
"""

import json
import os
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RULES = os.path.join(os.path.dirname(__file__), "rules", "t10_legal.json")
ORDER = {"red": 4, "orange": 3, "yellow": 2, "green": 1}


def main():
    ap = argparse.ArgumentParser(description="T10 法律风险检查")
    ap.add_argument("--text", required=True)
    ap.add_argument("--checkpoint")
    ap.add_argument("--rules", default=RULES)
    args = ap.parse_args()

    with open(args.rules, "r", encoding="utf-8") as f:
        rules = json.load(f)["rules"]

    risks = []
    for r in rules:
        if args.checkpoint and r["checkpoint"] != args.checkpoint:
            continue
        hit = [p for p in r["patterns"] if p in args.text]
        if not hit:
            continue
        risks.append({
            "risk_id": r["id"],
            "checkpoint": r["checkpoint"],
            "level": r["level"],
            "domain": r["domain"],
            "issue": r["issue"],
            "consequence": r["consequence"],
            "alternative": r["alternative"],
            "needs_lawyer": r["needs_lawyer"],
            "confidence": r["confidence"],
            "matched": hit,
        })

    risks.sort(key=lambda x: ORDER[x["level"]], reverse=True)
    blocked = any(x["level"] == "red" for x in risks)
    if not risks:
        risks = [{"risk_id": "L-GREEN", "checkpoint": args.checkpoint or "C5", "level": "green",
                  "domain": "—", "issue": "未发现明显风险", "consequence": "—",
                  "alternative": "—", "needs_lawyer": False, "confidence": 0.5, "matched": []}]
    report = {
        "ok": True,
        "blocked": blocked,
        "highest_level": risks[0]["level"] if risks else "green",
        "risks": risks,
        "disclaimer": "风险提示，不构成法律意见；重大事项请咨询执业律师；默认中国法域。",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
