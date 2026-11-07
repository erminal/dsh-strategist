#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T5 求解器（标准库）：期望值 / 零和矩阵最小最大

用法：
    python tools/t5_solve.py expected --plans examples/case4/plans.json
    python tools/t5_solve.py minimax  --matrix <matrix.json>

输出：calc_results JSON（数值 + 公式 + 来源标记），退出码 0。
定位：数字由代码算，不由 LLM 猜；不生成策略建议。
"""

import json
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TOL = 1e-6


def solve_expected(plans_path):
    with open(plans_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    plans = data.get("plans", [])
    errors, results = [], []
    for i, p in enumerate(plans):
        name = p.get("name", f"plan-{i}")
        outcomes = p.get("outcomes", [])
        if not outcomes:
            errors.append(f"{name}: 无结果")
            continue
        total = sum(o.get("prob", 0) for o in outcomes)
        if abs(total - 1.0) > 1e-4:
            errors.append(f"{name}: 概率和={total}，不等于 1")
            continue
        ev = 0.0
        parts = []
        for o in outcomes:
            ev += o["prob"] * o["value"]
            parts.append(f"{o['prob']}*{o['value']}")
        results.append({
            "calc_id": f"calc-{i+1}",
            "tool": "expected_value",
            "plan": name,
            "inputs": outcomes,
            "formula": " + ".join(parts),
            "result": round(ev, 4),
            "assumption": True,
            "notes": ["概率为假设，未校准"],
        })
    results.sort(key=lambda r: r["result"], reverse=True)
    best = results[0]["plan"] if results else None
    report = {"ok": not errors, "best_plan": best, "results": results, "errors": errors}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def solve_minimax(matrix_path):
    with open(matrix_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    m = data.get("matrix", [])
    if not m or not all(isinstance(row, list) and len(row) == len(m[0]) for row in m):
        print(json.dumps({"ok": False, "error": "matrix 必须是等长二维数组"}, ensure_ascii=False, indent=2))
        return 1
    row_mins = [min(row) for row in m]
    col_maxs = [max(m[i][j] for i in range(len(m))) for j in range(len(m[0]))]
    maximin = max(row_mins)
    minimax = min(col_maxs)
    saddle = None
    for i, row in enumerate(m):
        for j, v in enumerate(row):
            if v == maximin == minimax:
                saddle = [i, j]
    report = {
        "ok": True,
        "matrix": m,
        "row_mins": row_mins,
        "col_maxs": col_maxs,
        "maximin": maximin,
        "minimax": minimax,
        "saddle_point": saddle,
        "interpretation": "存在纯策略鞍点" if saddle is not None else "无纯策略鞍点，可能需要混合策略",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description="T5 求解器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("expected")
    e.add_argument("--plans", required=True)
    m = sub.add_parser("minimax")
    m.add_argument("--matrix", required=True)
    args = ap.parse_args()
    if args.cmd == "expected":
        return solve_expected(args.plans)
    return solve_minimax(args.matrix)


if __name__ == "__main__":
    sys.exit(main())
