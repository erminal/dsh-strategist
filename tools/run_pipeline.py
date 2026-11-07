#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主链路：把 T0–T11 串成一条命令（标准库）

用法：
    python tools/run_pipeline.py --case examples/case4 --out examples/case4/_run
    python tools/run_pipeline.py --case examples/case4 --out ... --no-log

约定 case 目录：
    background.txt   背景文本（S0）
    goal.json        目标卡（T0）
    sir.json         局势卡（T1）
    game_input.json  {"me_actions":[...], "opp_actions":[...], "payoffs":"payoffs.json"}
    payoffs.json     收益列表（可选）
    plans.json       期望值输入（可选）
    tree_spec.json   分支树输入（可选）
    decision.json    决策卡（T7）

输出：pipeline_report.json（每步 ok/exit/log/摘要）；任一步失败返回 1。
"""

import json
import os
import sys
import subprocess
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
PY = sys.executable


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_step(name, cmd, outdir):
    log = os.path.join(outdir, f"{name}.log")
    with open(log, "w", encoding="utf-8") as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    data = None
    try:
        with open(log, "r", encoding="utf-8") as f:
            txt = f.read().strip()
        data = json.loads(txt) if txt.startswith("{") else None
    except Exception:
        pass
    return {"name": name, "exit": p.returncode, "log": log, "data": data,
            "ok": p.returncode == 0}


def main():
    ap = argparse.ArgumentParser(description="主链路 T0–T11")
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "pipeline.db"))
    ap.add_argument("--no-log", action="store_true", help="不写 T8 日志")
    args = ap.parse_args()

    case = os.path.abspath(args.case)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    def p(rel):
        return os.path.join(case, rel)

    steps = []
    bg = read_text(p("background.txt")) if os.path.exists(p("background.txt")) else ""

    if os.path.exists(p("goal.json")):
        steps.append(run_step("T0_goal", [PY, os.path.join(TOOLS, "check.py"), "goal", p("goal.json")], out))
    if os.path.exists(p("sir.json")):
        steps.append(run_step("T1_sir", [PY, os.path.join(TOOLS, "check.py"), "sir", p("sir.json")], out))
    if bg:
        steps.append(run_step("T2_tag", [PY, os.path.join(TOOLS, "t2_tag.py"), p("background.txt")], out))
    if os.path.exists(p("sir.json")):
        steps.append(run_step("T3_retrieve", [PY, os.path.join(TOOLS, "t3_retrieve.py"), p("sir.json"), "--top-k", "5"], out))

    game_spec = os.path.join(out, "game_spec.json")
    if os.path.exists(p("game_input.json")):
        gi = json.loads(read_text(p("game_input.json")))
        cmd = [PY, os.path.join(TOOLS, "t4_build.py"), "--sir", p("sir.json"),
               "--me-actions", "|".join(gi.get("me_actions", [])),
               "--opp-actions", "|".join(gi.get("opp_actions", [])),
               "--out", game_spec]
        if gi.get("payoffs") and os.path.exists(p(gi["payoffs"])):
            cmd += ["--payoffs", p(gi["payoffs"])]
        steps.append(run_step("T4_build", cmd, out))

    if os.path.exists(p("plans.json")):
        steps.append(run_step("T5_solve", [PY, os.path.join(TOOLS, "t5_solve.py"), "expected",
                                           "--plans", p("plans.json")], out))
    if os.path.exists(game_spec) and os.path.exists(p("tree_spec.json")):
        steps.append(run_step("T6_tree", [PY, os.path.join(TOOLS, "t6_tree.py"),
                                          "--game", game_spec, "--tree", p("tree_spec.json")], out))
    if os.path.exists(p("decision.json")):
        steps.append(run_step("T7_decision", [PY, os.path.join(TOOLS, "check.py"), "decision", p("decision.json")], out))
    if bg:
        steps.append(run_step("T10_legal", [PY, os.path.join(TOOLS, "t10_legal.py"), "--text", bg], out))
        steps.append(run_step("T11_mind", [PY, os.path.join(TOOLS, "t11_mind.py"), "--text", bg], out))
    if not args.no_log and os.path.exists(p("decision.json")):
        sir = json.loads(read_text(p("sir.json"))) if os.path.exists(p("sir.json")) else {}
        steps.append(run_step("T8_log", [PY, os.path.join(TOOLS, "t8_log.py"), "--db", args.db, "record",
                                         "--decision", p("decision.json"), "--session", os.path.basename(case),
                                         "--structure", (sir.get("structure") or {}).get("primary", ""),
                                         "--goal-type", (sir.get("goal") or {}).get("type", "")], out))

    # T10 red 允许 exit=1（blocked）
    for s in steps:
        if s["name"] == "T10_legal" and s["data"] is not None:
            s["ok"] = True
            s["blocked"] = bool(s["data"].get("blocked"))

    report = {
        "ok": all(s["ok"] for s in steps),
        "case": case,
        "steps": [{k: s.get(k) for k in ("name", "ok", "exit", "log", "blocked")} for s in steps],
        "summaries": {
            "T3_top": (steps[3]["data"] or {}).get("results", [])[:3] if len(steps) > 3 else [],
            "T5_best": None,
            "T6_checks": None,
            "T10_highest": None,
        },
    }
    for s in steps:
        if s["name"] == "T5_solve" and s["data"]:
            report["summaries"]["T5_best"] = s["data"].get("best_plan")
        if s["name"] == "T6_tree" and s["data"]:
            report["summaries"]["T6_checks"] = s["data"].get("checks")
        if s["name"] == "T10_legal" and s["data"]:
            report["summaries"]["T10_highest"] = s["data"].get("highest_level")

    report_path = os.path.join(out, "pipeline_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": report["ok"], "report": report_path,
                      "steps": report["steps"], "summaries": report["summaries"]},
                     ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
