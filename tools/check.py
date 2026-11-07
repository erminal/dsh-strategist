#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T0/T1/T7 最小校验器（Python 标准库，无第三方依赖）

用法：
    python tools/check.py goal      <goal.json>
    python tools/check.py sir       <sir.json>
    python tools/check.py decision  <decision.json>

输出：JSON 报告（ok / errors / warnings / stats），退出码 0=通过，1=不通过。
定位：LLM 负责「抽取/生成」，本工具负责「结构校验 + 硬门槛」，是防幻觉的代码闸门。
"""

import json
import os
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

GOAL_TYPES = {"attack", "defensive", "maintain", "probe", "exit", "mixed"}
STRUCTURES = {"distribution", "competition", "coordination", "authority", "relationship"}
SOURCES = {"user", "cited", "calculated", "assumption", "inferred"}
FACT_STATUS = {"provable", "claim", "unverified", "inferred"}
GAP_TYPES = {"fact", "intent", "structure", "capability", "dynamic", "profile"}
ASK_WHO = {"opponent", "third_party", "public"}
ETHICS = {"green", "gray", "red"}
LEGAL_LEVELS = {"red", "orange", "yellow", "green"}

TAGS = ["power", "info", "time", "relation", "third_party", "reversibility", "stakes"]

STRUCTURE_REQUIRED = {
    "distribution": ["BATNA/替代方案", "可分配标的", "底线", "时间压力", "承诺可信度"],
    "competition": ["决策者", "评价标准", "双方筹码", "可承受损失", "时间窗口"],
    "coordination": ["共同目标", "投入与收益", "监督方式", "背叛诱因", "退出成本"],
    "authority": ["上级目标/考核", "信息差", "风险偏好", "授权边界", "汇报节奏"],
    "relationship": ["关系历史", "信任额度", "长期收益", "边界", "回报预期"],
}

DECISION_REQUIRED = [
    "conclusion", "situation", "candidates", "recommendation", "reasons",
    "countermeasures", "steps", "signals", "fail_criteria", "plan_b",
    "confidence", "assumptions", "ethics_check", "legal_check", "sources",
]
DECISION_COUNTER_MIN = 2


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_known_cards():
    """从仓库索引加载已知卡 id（模型卡/计策卡/变体卡/变体组）。找不到文件时返回空集合。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    known = set()

    def read_json(rel):
        p = os.path.join(root, rel)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    uv = read_json("kb/index/unified-variants.json")
    if uv:
        for g in uv.get("groups", []):
            if g.get("card_id"):
                known.add(g["card_id"])
            known.add(g.get("id"))
            known.update(g.get("members", []))
    ci = read_json("kb/meta/cards-index.json")
    if ci:
        for b in ci.get("batches", []):
            for c in b.get("cards", []):
                known.add(c.get("id"))
    si = read_json("kb/meta/stratagem-index.json")
    if si:
        for c in si.get("cards", []):
            known.add(c.get("id"))
    return known


def err(errors, path, msg):
    errors.append(f"{path}: {msg}" if path else msg)


def check_enum(errors, path, value, allowed):
    if value not in allowed:
        err(errors, path, f"取值 {value!r} 不在允许集合 {sorted(allowed)}")


def check_str_list(errors, path, value, min_len=0):
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        err(errors, path, "必须是字符串数组")
        return
    if len([x for x in value if x.strip()]) < min_len:
        err(errors, path, f"至少需要 {min_len} 条非空内容")


# ---------- T0 目标卡 ----------

def check_goal(goal, errors, warnings):
    for k in ["goal_id", "type", "ultimate", "direct", "success_criteria",
              "unacceptable", "non_goals", "relationship_budget", "time_window",
              "constraints", "confidence"]:
        if k not in goal:
            err(errors, "goal", f"缺少字段 {k}")
    check_enum(errors, "goal.type", goal.get("type"), GOAL_TYPES)
    rb = goal.get("relationship_budget")
    if not isinstance(rb, (int, float)) or not (0 <= rb <= 3):
        err(errors, "goal.relationship_budget", "必须是 0–3 的数字")
    check_str_list(errors, "goal.success_criteria", goal.get("success_criteria"), 1)
    check_str_list(errors, "goal.unacceptable", goal.get("unacceptable"), 1)
    check_str_list(errors, "goal.non_goals", goal.get("non_goals"), 0)
    c = goal.get("confidence")
    if not isinstance(c, (int, float)) or not (0 <= c <= 1):
        err(errors, "goal.confidence", "必须是 0–1 的数字")
    if goal.get("type") in {"defensive", "exit"} and not goal.get("success_criteria"):
        warnings.append("否定/退出型目的建议写清「什么算达成」")


# ---------- T1 局势卡 ----------

def check_sir(sir, errors, warnings):
    for k in ["schema_version", "situation_id", "round", "goal", "actors",
              "facts", "unknowns", "structure", "tags", "completeness"]:
        if k not in sir:
            err(errors, "sir", f"缺少字段 {k}")
    if "goal" in sir:
        g_errors, g_warn = [], []
        check_goal(sir["goal"], g_errors, g_warn)
        errors.extend("sir." + e for e in g_errors)
        warnings.extend("sir." + w for w in g_warn)

    actors = sir.get("actors") or []
    if not isinstance(actors, list) or not actors:
        err(errors, "sir.actors", "必须是非空数组")
    else:
        for i, a in enumerate(actors):
            for k in ["id", "role", "source"]:
                if k not in a:
                    err(errors, f"sir.actors[{i}]", f"缺少 {k}")
            if "decision_maker" not in a:
                err(errors, f"sir.actors[{i}]", "缺少 decision_maker")
            check_enum(errors, f"sir.actors[{i}].source", a.get("source"), SOURCES)

    facts = sir.get("facts") or []
    for i, f in enumerate(facts):
        for k in ["id", "text", "status", "source", "confidence"]:
            if k not in f:
                err(errors, f"sir.facts[{i}]", f"缺少 {k}")
        check_enum(errors, f"sir.facts[{i}].status", f.get("status"), FACT_STATUS)
        check_enum(errors, f"sir.facts[{i}].source", f.get("source"), SOURCES)
        if f.get("status") in {"claim", "unverified"}:
            warnings.append(f"事实 {f.get('id')} 为 {f.get('status')}，输出需标注未核实")

    st = sir.get("structure") or {}
    check_enum(errors, "sir.structure.primary", st.get("primary"), STRUCTURES)
    if st.get("secondary") is not None:
        check_enum(errors, "sir.structure.secondary", st.get("secondary"), STRUCTURES)

    tags = sir.get("tags") or {}
    for t in TAGS:
        if t not in tags:
            err(errors, "sir.tags", f"缺少标签 {t}")

    comp = sir.get("completeness") or {}
    score = comp.get("score")
    if not isinstance(score, (int, float)) or not (0 <= score <= 1):
        err(errors, "sir.completeness.score", "必须是 0–1 的数字")
    gaps = sir.get("info_gaps") or []
    if isinstance(score, (int, float)) and score < 0.7 and len(gaps) == 0:
        err(errors, "sir.completeness", "完备度 < 0.7 时必须给出 info_gaps（追问清单）")
    for i, g in enumerate(gaps):
        for k in ["gap_id", "type", "field", "impact", "uncertainty", "cost",
                  "how", "questions", "ask_who", "ethics"]:
            if k not in g:
                err(errors, f"sir.info_gaps[{i}]", f"缺少 {k}")
        check_enum(errors, f"sir.info_gaps[{i}].type", g.get("type"), GAP_TYPES)
        check_enum(errors, f"sir.info_gaps[{i}].ask_who", g.get("ask_who"), ASK_WHO)
        check_enum(errors, f"sir.info_gaps[{i}].ethics", g.get("ethics"), ETHICS)

    legal = sir.get("legal_risks") or []
    for i, l in enumerate(legal):
        check_enum(errors, f"sir.legal_risks[{i}].level", l.get("level"), LEGAL_LEVELS)
        if l.get("level") == "red":
            warnings.append("存在 red 法律风险，输出前必须拦截或给合法替代")

    if st.get("primary") in STRUCTURE_REQUIRED:
        warnings.append("该结构必填项：" + "、".join(STRUCTURE_REQUIRED[st["primary"]]))


# ---------- T7 决策卡 ----------

def check_decision(d, errors, warnings):
    for k in DECISION_REQUIRED:
        if k not in d:
            err(errors, "decision", f"缺少字段 {k}")
    if not isinstance(d.get("conclusion"), str) or not d.get("conclusion", "").strip():
        err(errors, "decision.conclusion", "不能为空")

    cm = d.get("countermeasures")
    if not isinstance(cm, list) or len([x for x in cm if isinstance(x, str) and x.strip()]) < DECISION_COUNTER_MIN:
        err(errors, "decision.countermeasures", f"至少 {DECISION_COUNTER_MIN} 条具体反制")

    if not (d.get("fail_criteria") or d.get("plan_b")):
        err(errors, "decision", "必须给出失败判据或 Plan B")

    check_enum(errors, "decision.ethics_check.level", (d.get("ethics_check") or {}).get("level"), ETHICS)
    lvl = (d.get("legal_check") or {}).get("level")
    check_enum(errors, "decision.legal_check.level", lvl, LEGAL_LEVELS)
    if lvl == "red":
        err(errors, "decision.legal_check", "法律风险为 red，禁止输出")

    used = d.get("cards_used") or []
    if isinstance(used, list):
        for cid in used:
            if isinstance(cid, str) and "meiren" in cid or isinstance(cid, str) and "kurou" in cid:
                err(errors, "decision.cards_used", f"red 卡 {cid} 不得进入现实建议")
        known = load_known_cards()
        if known:
            for cid in used:
                if isinstance(cid, str) and cid not in known:
                    err(errors, "decision.cards_used", f"未知卡 id：{cid}")
        else:
            warnings.append("未加载卡索引，跳过 cards_used 存在性校验")

    src = d.get("sources")
    if not isinstance(src, list) or not any(isinstance(x, str) and x.strip() for x in src):
        err(errors, "decision.sources", "至少给出来源（用户/卡 id/计算 id）")

    if not isinstance(d.get("assumptions"), list):
        err(errors, "decision.assumptions", "必须是数组（可为空）")
    c = d.get("confidence")
    if not isinstance(c, (int, float)) or not (0 <= c <= 1):
        err(errors, "decision.confidence", "必须是 0–1 的数字")


# ---------- 入口 ----------

def main():
    ap = argparse.ArgumentParser(description="T0/T1/T7 最小校验器")
    ap.add_argument("kind", choices=["goal", "sir", "decision"])
    ap.add_argument("path")
    args = ap.parse_args()

    try:
        data = load(args.path)
    except Exception as e:
        print(json.dumps({"ok": False, "errors": [f"读取失败: {e}"], "warnings": []},
                         ensure_ascii=False, indent=2))
        return 1

    errors, warnings = [], []
    if args.kind == "goal":
        check_goal(data, errors, warnings)
    elif args.kind == "sir":
        check_sir(data, errors, warnings)
    else:
        check_decision(data, errors, warnings)

    report = {
        "kind": args.kind,
        "file": args.path,
        "ok": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
