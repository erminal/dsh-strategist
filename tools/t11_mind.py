#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11 心性评估与引导（规则版，标准库）

用法：
    python tools/t11_mind.py --text "我气得想马上发消息骂他"
    python tools/t11_mind.py --text "最近很累，反复检查消息"

输出：self_state + mindset_card（心法卡）+ need_confirm。只做自我觉察，不做心理诊断。
"""

import json
import os
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RULES = os.path.join(os.path.dirname(__file__), "rules", "t11_mind.json")


def main():
    ap = argparse.ArgumentParser(description="T11 心性评估与引导")
    ap.add_argument("--text", required=True)
    ap.add_argument("--rules", default=RULES)
    args = ap.parse_args()

    with open(args.rules, "r", encoding="utf-8") as f:
        rules = json.load(f)["rules"]

    matched = [r for r in rules if any(p in args.text for p in r["patterns"])]
    if not matched:
        matched = [r for r in rules if r["id"] == "M-CALM"]
    top = max(matched, key=lambda r: r["emotion"])

    biases, needs = [], []
    for r in matched:
        for b in r.get("biases", []):
            if b not in biases:
                biases.append(b)
        for n in r.get("needs", []):
            if n not in needs:
                needs.append(n)

    self_state = {
        "emotion_intensity": top["emotion"],
        "stress": max(r["stress"] for r in matched),
        "biases": biases,
        "motivation": "emotion" if top["emotion"] >= 4 else "result",
        "inner_needs": needs,
        "confidence": 0.4,
        "source": "inferred",
    }
    card = {
        "anchor": top["anchor"],
        "actions": top["actions"],
        "reminder": "你现在想赢，还是想解决问题？",
        "pause": any(r.get("pause") for r in matched),
    }
    report = {
        "ok": True,
        "self_state": self_state,
        "mindset_card": card,
        "need_confirm": True,
        "note": "推断结果需用户确认；未确认只作假设。若情绪持续严重，建议寻求专业帮助。",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
