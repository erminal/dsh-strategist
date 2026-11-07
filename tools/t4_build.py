#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T4 博弈结构构建（标准库）

用法：
    python tools/t4_build.py --sir examples/case4/sir.json \
        --me-actions "电话+书面分期|直接律师函|找共同朋友调解" \
        --opp-actions "继续拖|接受分期|翻脸失联" \
        --payoffs examples/case4/payoffs.json \
        --out /tmp/game_spec.json

输出：game_spec JSON（players/actions/payoffs/information/timing/assumptions/unknowns）。
定位：LLM 只提议，代码校验收益来源；不求解（T5 负责）。
"""

import json
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SOURCES = {"user", "range", "assumption", "qualitative"}


def split_actions(s):
    if not s:
        return []
    for sep in ["|", ",", "，"]:
        if sep in s:
            return [x.strip() for x in s.split(sep) if x.strip()]
    return [s.strip()]


def main():
    ap = argparse.ArgumentParser(description="T4 博弈结构构建")
    ap.add_argument("--sir", required=True)
    ap.add_argument("--me-actions", required=True)
    ap.add_argument("--opp-actions", required=True)
    ap.add_argument("--payoffs", help="收益列表 JSON（可选）")
    ap.add_argument("--out", help="输出文件（默认 stdout）")
    ap.add_argument("--game-id", default="game-001")
    args = ap.parse_args()

    errors, warnings = [], []
    with open(args.sir, "r", encoding="utf-8") as f:
        sir = json.load(f)

    me = split_actions(args.me_actions)
    opp = split_actions(args.opp_actions)
    if len(me) < 2 or len(opp) < 2:
        errors.append("双方动作各至少 2 个")
    if len(me) > 4 or len(opp) > 4:
        warnings.append("动作超过 4 个，分支会膨胀")

    payoffs = []
    if args.payoffs:
        with open(args.payoffs, "r", encoding="utf-8") as f:
            payoffs = json.load(f)
        if not isinstance(payoffs, list):
            errors.append("payoffs 必须是数组")
            payoffs = []
        for i, p in enumerate(payoffs):
            for k in ["player", "action", "opp_action", "value", "source"]:
                if k not in p:
                    errors.append(f"payoffs[{i}] 缺少 {k}")
            if p.get("source") not in SOURCES:
                errors.append(f"payoffs[{i}].source 非法：{p.get('source')}")

    info = {}
    for a in sir.get("actors", []):
        info[a.get("id")] = a.get("resources", [])
    timing = {"rounds": sir.get("round", 1), "first": "A"}
    spec = {
        "ok": len(errors) == 0,
        "game_id": args.game_id,
        "players": [
            {"id": "A", "role": "me", "actions": me},
            {"id": "B", "role": "opponent", "actions": opp},
        ],
        "payoffs": payoffs,
        "information": info,
        "timing": timing,
        "assumptions": ["收益量级/概率需用户确认"] if payoffs else [],
        "unknowns": sir.get("unknowns", []),
        "errors": errors,
        "warnings": warnings,
    }
    text = json.dumps(spec, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(json.dumps({"ok": len(errors) == 0, "out": args.out, "errors": errors, "warnings": warnings},
                         ensure_ascii=False, indent=2))
    else:
        print(text)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
