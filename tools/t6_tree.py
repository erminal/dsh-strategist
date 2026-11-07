#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T6 分支树（标准库）

用法：
    python tools/t6_tree.py --game /tmp/game_spec.json --tree examples/case4/tree_spec.json \
        --max-depth 3 --max-branches 4

输入：
    game_spec.json（T4 输出）
    tree_spec.json：{"actions":[{"action":"...","reactions":[{"reaction":"...","prob":0.5,"payoff":7,"source":"assumption"}]}]}
输出：
    tree JSON（nodes/edges/概率/收益/依据 + checks），退出码 0/1。
定位：LLM 提议动作与反应，代码做存在性、归一化、深度/宽度校验。
"""

import json
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SOURCES = {"user", "range", "assumption", "qualitative", "calc"}
TOL = 1e-6


def main():
    ap = argparse.ArgumentParser(description="T6 分支树")
    ap.add_argument("--game", required=True)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--max-branches", type=int, default=4)
    ap.add_argument("--min-prob", type=float, default=0.05)
    args = ap.parse_args()

    with open(args.game, "r", encoding="utf-8") as f:
        game = json.load(f)
    with open(args.tree, "r", encoding="utf-8") as f:
        spec = json.load(f)

    players = {p["id"]: p for p in game.get("players", [])}
    a_actions = set(players.get("A", {}).get("actions", []))
    b_actions = set(players.get("B", {}).get("actions", []))

    errors, warnings = [], []
    nodes, edges = [], []
    nodes.append({"id": "root", "type": "decision", "player": "A", "label": "选择动作"})

    actions = spec.get("actions", [])
    if len(actions) > args.max_branches:
        warnings.append(f"动作数 {len(actions)} 超过 max-branches={args.max_branches}，仅处理前 {args.max_branches}")
        actions = actions[: args.max_branches]

    if len(actions) < len(a_actions):
        warnings.append(f"仅覆盖 {len(actions)}/{len(a_actions)} 个我方动作")

    for ai, a in enumerate(actions):
        label = a.get("action")
        if label not in a_actions:
            errors.append(f"未知我方动作：{label}")
            continue
        aid = f"a{ai+1}"
        nodes.append({"id": aid, "type": "action", "player": "A", "label": label})
        edges.append({"from": "root", "to": aid})
        reactions = a.get("reactions", [])
        if len(reactions) > args.max_branches:
            warnings.append(f"{label}: 反应数超过 max-branches，截断")
            reactions = reactions[: args.max_branches]
        total = sum(r.get("prob", 0) for r in reactions)
        if abs(total - 1.0) > TOL:
            errors.append(f"{label}: 反应概率和={total}，不等于 1")
        for ri, r in enumerate(reactions):
            rlabel = r.get("reaction")
            if rlabel not in b_actions:
                errors.append(f"{label}: 未知对方反应 {rlabel}")
                continue
            if r.get("source") not in SOURCES:
                errors.append(f"{label}/{rlabel}: source 非法")
            rid = f"{aid}-r{ri+1}"
            node = {
                "id": rid,
                "type": "reaction",
                "player": "B",
                "label": rlabel,
                "prob": r.get("prob"),
                "payoff": r.get("payoff"),
                "source": r.get("source"),
            }
            if r.get("prob") is not None and r["prob"] < args.min_prob:
                node["pruned"] = True
                warnings.append(f"{label}/{rlabel}: 概率低于 {args.min_prob}，标记剪枝")
            nodes.append(node)
            edges.append({"from": aid, "to": rid})

    tree = {
        "ok": not errors,
        "tree_id": spec.get("tree_id", "t-001"),
        "max_depth": args.max_depth,
        "max_branches": args.max_branches,
        "nodes": nodes,
        "edges": edges,
        "checks": {
            "prob_sum_ok": not any("概率和" in e for e in errors),
            "action_count": len(actions),
            "node_count": len(nodes),
        },
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(tree, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
