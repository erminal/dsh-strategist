#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T3 检索（标准库，无依赖）

用法：
    python tools/t3_retrieve.py examples/case4/sir.json
    python tools/t3_retrieve.py --structure competition --secondary authority \
        --goal-type attack --tags '{"info":"one_sided","stakes":"high"}' --top-k 5

输入：SIR JSON（或命令行参数）
输出：JSON（变体 + 原则 + 成员 + 命中理由），退出码 0。
定位：机制/标签 → 47 变体 → 20 原则 → 成员卡；red 变体只进 defense_only。
"""

import json
import os
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 结构 → 候选机制（第一个是首选）
STRUCTURE_PREF = {
    "competition": ["M4", "M9", "M1"],
    "distribution": ["M5", "M6"],
    "coordination": ["M3", "M6", "M11", "M5"],
    "authority": ["M1", "M9", "M12", "M4"],
    "relationship": ["M6", "M12", "M8"],
}

# 标签值 → 加成的机制
TAG_BOOST = {
    "info": {"one_sided": ["M1"], "mutual_blind": ["M1", "M10"]},
    "time": {"me_urgent": ["M2"], "them_urgent": ["M2"]},
    "relation": {"repeated": ["M6", "M3"], "one_shot": ["M6"]},
    "third_party": {"audience": ["M3", "M12"], "arbiter": ["M12"]},
    "reversibility": {"irreversible": ["M6", "M8"]},
    "stakes": {"high": ["M4", "M9"]},
}

# 结构 → 核心变体加成（提升语义相关性）
CORE_BOOST = {
    "distribution": {"V5-3": 5, "V5-4": 4},
    "competition": {"V4-1": 5, "V9-1": 4, "V1-1": 3},
    "coordination": {"V3-1": 5, "V5-6": 8, "V6-3": 3},
    "authority": {"V12-3": 4, "V6-1": 3, "V2-2": 3},
    "relationship": {"V6-3": 5, "V12-1": 4, "V8-1": 3},
}

# 目的类型 → 加成的机制
GOAL_BOOST = {
    "attack": ["M4", "M9"],
    "defensive": ["M6", "M8"],
    "maintain": ["M6", "M12"],
    "probe": ["M10"],
    "exit": ["M8"],
    "mixed": [],
}


def load_json(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data():
    uv = load_json("kb/index/unified-variants.json")
    pi = load_json("kb/meta/principle-index.json")
    if uv is None:
        raise SystemExit("缺少 kb/index/unified-variants.json")
    pnames = {}
    if pi:
        for p in pi.get("cards", []):
            pnames[p["id"]] = p.get("name", p["id"])
    return uv["groups"], pnames


def mech_of(g):
    """兼容索引里的 mechanism / mech 两种写法。"""
    m = g.get("mechanism")
    if m:
        return m
    return {"primary": g.get("mech"), "secondary": []}


def score_variant(g, structure, secondary, tags, goal_type):
    score = 0.0
    why = []
    mech = mech_of(g)
    primary = mech.get("primary")
    secs = mech.get("secondary") or []

    pref = STRUCTURE_PREF.get(structure or "", [])
    if pref and primary == pref[0]:
        score += 4
        why.append(f"主结构 {structure} 首选机制 {primary}")
    elif primary in pref:
        score += 3
        why.append(f"主结构 {structure} 命中机制 {primary}")

    if secondary:
        pref2 = STRUCTURE_PREF.get(secondary, [])
        if primary in pref2:
            score += 2
            why.append(f"次结构 {secondary} 命中机制 {primary}")

    for m in secs:
        if m in pref or (secondary and m in STRUCTURE_PREF.get(secondary, [])):
            score += 1
            why.append(f"次机制 {m} 命中")

    for tag_key, tag_val in (tags or {}).items():
        mechs = TAG_BOOST.get(tag_key, {}).get(tag_val, [])
        if primary in mechs:
            score += 2
            why.append(f"标签 {tag_key}={tag_val} → {primary}")
        for m in secs:
            if m in mechs:
                score += 1
                why.append(f"标签 {tag_key}={tag_val} → 次机制 {m}")

    for m in GOAL_BOOST.get(goal_type or "", []):
        if primary == m:
            score += 1
            why.append(f"目的类型 {goal_type} → {m}")

    for st in (structure, secondary):
        boost = (CORE_BOOST.get(st or "") or {}).get(g.get("id"))
        if boost:
            score += boost
            why.append(f"核心变体加成（{st}）")

    return score, why


def main():
    ap = argparse.ArgumentParser(description="T3 检索（机制/标签 → 变体/原则）")
    ap.add_argument("sir", nargs="?", help="SIR JSON 文件")
    ap.add_argument("--structure")
    ap.add_argument("--secondary")
    ap.add_argument("--goal-type")
    ap.add_argument("--tags", help='JSON 字符串，如 {"info":"one_sided"}')
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    structure = args.structure
    secondary = args.secondary
    goal_type = args.goal_type
    tags = {}

    if args.sir:
        with open(args.sir, "r", encoding="utf-8") as f:
            sir = json.load(f)
        st = sir.get("structure") or {}
        structure = structure or st.get("primary")
        secondary = secondary or st.get("secondary")
        goal_type = goal_type or (sir.get("goal") or {}).get("type")
        tags = sir.get("tags") or {}

    if args.tags:
        try:
            tags.update(json.loads(args.tags))
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "--tags 不是合法 JSON"}, ensure_ascii=False, indent=2))
            return 1

    if not structure:
        print(json.dumps({"ok": False, "error": "缺少 structure"}, ensure_ascii=False, indent=2))
        return 1

    groups, pnames = load_data()
    results, defense_only = [], []

    for g in groups:
        if g.get("ethics") == "red":
            defense_only.append({
                "variant_id": g["id"],
                "card_id": g.get("card_id"),
                "name": g.get("name"),
                "ethics": "red",
                "note": "仅防御识别，不进入现实建议",
            })
            continue
        score, why = score_variant(g, structure, secondary, tags, goal_type)
        if score <= 0:
            continue
        results.append({
            "variant_id": g["id"],
            "card_id": g.get("card_id"),
            "name": g.get("name"),
            "score": round(score, 2),
            "mechanism": mech_of(g),
            "principles": [pnames.get(p, p) for p in g.get("principles", [])],
            "principle_ids": g.get("principles", []),
            "members": g.get("members", []),
            "why": why,
        })

    results.sort(key=lambda r: (r["score"], len(r["principles"])), reverse=True)
    # 先保证主/次结构的首选机制各有覆盖，再按分数与多样性补齐
    top, seen = [], {}
    required = []
    if structure:
        required.append(STRUCTURE_PREF.get(structure, [None])[0])
    if secondary:
        required.append(STRUCTURE_PREF.get(secondary, [None])[0])
    for req in required:
        if not req:
            continue
        for r in results:
            if (r.get("mechanism") or {}).get("primary") == req and r not in top:
                r["coverage_pick"] = True
                top.append(r)
                seen[req] = seen.get(req, 0) + 1
                break
    for r in results:
        if len(top) >= args.top_k:
            break
        if r in top:
            continue
        pm = (r.get("mechanism") or {}).get("primary")
        if seen.get(pm, 0) >= 2:
            continue
        top.append(r)
        seen[pm] = seen.get(pm, 0) + 1
    if len(top) < args.top_k:
        for r in results:
            if r not in top:
                top.append(r)
            if len(top) >= args.top_k:
                break
    # 显示层：始终按分数排序；结构覆盖只作为标记，不影响顺序
    top.sort(key=lambda r: (r.get("score", 0), len(r.get("principles", []))), reverse=True)
    report = {
        "ok": True,
        "query": {"structure": structure, "secondary": secondary, "goal_type": goal_type, "tags": tags},
        "count": len(top),
        "results": top,
        "coverage_picks": [r["variant_id"] for r in top if r.get("coverage_pick")],
        "defense_only": defense_only,
        "fallback": None if top else "无匹配变体（请补充结构/标签/目的）",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
