#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T2 结构与标签判定（规则版，标准库，无依赖）

用法：
    python tools/t2_tag.py --text "文本"
    python tools/t2_tag.py examples/case4/background.txt

输出：JSON（structure top1/top2、tags 建议、rule_hits），退出码 0。
定位：可审计的规则判定；低置信输出两个候选，交 T1b 追问。
"""

import json
import os
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

THRESHOLD = 0  # 关键词命中即计分
TOP2_RATIO = 0.8  # top2/top1 >= 0.8 时视为不确定


def load_rules(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def score_structures(text, rules):
    scores = {}
    hits = []
    for struct, rule_groups in rules["structures"].items():
        s = 0.0
        for g in rule_groups:
            w = g.get("weight", 1.0)
            for kw in g["keywords"]:
                n = text.count(kw)
                if n > 0:
                    s += n * w
                    hits.append({"rule_id": g["id"], "keyword": kw, "target": struct, "count": n})
        scores[struct] = s
    return scores, hits


def judge_tags(text, rules):
    tags, tag_hits = {}, []
    for tag, rule_groups in rules["tags"].items():
        value, hit = "unknown", None
        for g in rule_groups:
            for kw in g["keywords"]:
                if kw in text:
                    hit = {"tag": tag, "value": g["value"], "keyword": kw}
                    break
            if hit:
                break
        tags[tag] = hit["value"] if hit else "unknown"
        if hit:
            tag_hits.append(hit)
    return tags, tag_hits


def main():
    ap = argparse.ArgumentParser(description="T2 结构与标签判定（规则版）")
    ap.add_argument("path", nargs="?", help="文本文件")
    ap.add_argument("--text", help="直接给文本")
    ap.add_argument("--rules", default=os.path.join(os.path.dirname(__file__), "rules", "t2_rules.json"))
    args = ap.parse_args()

    if args.text:
        text = args.text
    elif args.path:
        with open(args.path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        print(json.dumps({"ok": False, "error": "需要 --text 或文件路径"}, ensure_ascii=False))
        return 1

    rules = load_rules(args.rules)
    scores, hits = score_structures(text, rules)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top1, s1 = ranked[0] if ranked else ("unknown", 0)
    top2, s2 = ranked[1] if len(ranked) > 1 else (None, 0)
    if s1 == 0:
        structure = {"primary": "unknown", "secondary": None, "confidence": 0.0}
    else:
        conf = round(s1 / sum(v for _, v in ranked if v > 0), 2)
        structure = {"primary": top1, "secondary": top2, "confidence": conf}
        if s2 > 0 and s2 / s1 >= TOP2_RATIO:
            structure["uncertain"] = True

    tags, tag_hits = judge_tags(text, rules)
    report = {
        "ok": True,
        "structure": structure,
        "tags": tags,
        "rule_hits": hits,
        "tag_hits": tag_hits,
        "notes": ["规则版，低置信请交 T1b 追问"] if structure.get("uncertain") or structure["primary"] == "unknown" else [],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
