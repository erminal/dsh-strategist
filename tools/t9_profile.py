#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T9 对手画像（JSON 本地存储，标准库）

用法：
    python tools/t9_profile.py init --id p-B --subject "B（上级）" --intuition "他比较看数据"
    python tools/t9_profile.py evidence --id p-B --dim risk_appetite --estimate low --direction support --note "审批保守"
    python tools/t9_profile.py show --id p-B
    python tools/t9_profile.py list

规则：至少 2 条独立证据才把置信度升到 0.6 以上；冲突证据并列；30 天无更新置信度衰减。
默认目录：data/profiles（本地，不提交）。不做人格诊断。
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(ROOT, "data", "profiles")
DIMS = [
    "goals", "bottom_line", "risk_appetite", "time_preference",
    "information", "decision_style", "credibility", "patterns",
    "pressure_points", "network",
]


def now():
    return datetime.now()


def path_of(d, pid):
    return os.path.join(d, pid + ".json")


def load(d, pid):
    p = path_of(d, pid)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save(d, prof):
    os.makedirs(d, exist_ok=True)
    with open(path_of(d, prof["profile_id"]), "w", encoding="utf-8") as f:
        json.dump(prof, f, ensure_ascii=False, indent=2)


def blank(pid, subject, intuition):
    dims = {k: {"estimate": "unknown", "confidence": 0.1, "evidence": []} for k in DIMS}
    return {
        "profile_id": pid,
        "subject": subject,
        "version": 1,
        "user_intuition": intuition or "",
        "dimensions": dims,
        "hypotheses": [],
        "contradictions": [],
        "updated_at": now().isoformat(timespec="seconds"),
    }


def recompute(dim):
    ev = dim.get("evidence", [])
    support = sum(1 for e in ev if e.get("direction") == "support")
    oppose = sum(1 for e in ev if e.get("direction") == "oppose")
    n = support + oppose
    if n == 0:
        dim["confidence"] = 0.1
    elif n == 1:
        dim["confidence"] = 0.2
    else:
        base = min(0.9, 0.4 + 0.15 * n)
        if support and oppose:
            dim["confidence"] = round(min(0.5, max(0.2, base - 0.3)), 2)
            dim["estimate"] = "conflicting"
        else:
            dim["confidence"] = round(base, 2)


def cmd_init(args, d):
    if load(d, args.id):
        print(json.dumps({"ok": False, "error": f"画像 {args.id} 已存在"}, ensure_ascii=False, indent=2))
        return 1
    prof = blank(args.id, args.subject, args.intuition)
    save(d, prof)
    print(json.dumps({"ok": True, "profile": prof}, ensure_ascii=False, indent=2))
    return 0


def cmd_evidence(args, d):
    prof = load(d, args.id)
    if not prof:
        print(json.dumps({"ok": False, "error": f"画像 {args.id} 不存在，请先 init"}, ensure_ascii=False, indent=2))
        return 1
    if args.dim not in DIMS:
        print(json.dumps({"ok": False, "error": f"未知维度 {args.dim}，可用：{DIMS}"}, ensure_ascii=False, indent=2))
        return 1
    dim = prof["dimensions"][args.dim]
    ev = {
        "id": f"e{len(dim['evidence']) + 1}",
        "note": args.note or "",
        "direction": args.direction,
        "source": args.source,
        "date": now().isoformat(timespec="seconds"),
    }
    dim["evidence"].append(ev)
    if args.estimate:
        dim["estimate"] = args.estimate
    recompute(dim)
    prof["version"] += 1
    prof["updated_at"] = now().isoformat(timespec="seconds")
    save(d, prof)
    print(json.dumps({"ok": True, "dimension": args.dim, "estimate": dim["estimate"],
                      "confidence": dim["confidence"], "evidence_count": len(dim["evidence"])},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_show(args, d):
    prof = load(d, args.id)
    if not prof:
        print(json.dumps({"ok": False, "error": f"画像 {args.id} 不存在"}, ensure_ascii=False, indent=2))
        return 1
    # 30 天衰减
    try:
        updated = datetime.fromisoformat(prof["updated_at"])
        if now() - updated > timedelta(days=30):
            for dim in prof["dimensions"].values():
                dim["confidence"] = round(max(0.1, dim["confidence"] * 0.8), 2)
            prof["decayed"] = True
            prof["updated_at"] = now().isoformat(timespec="seconds")
            save(d, prof)
    except Exception:
        pass
    print(json.dumps({"ok": True, "profile": prof}, ensure_ascii=False, indent=2))
    return 0


def cmd_list(args, d):
    if not os.path.isdir(d):
        items = []
    else:
        items = []
        for fn in os.listdir(d):
            if fn.endswith(".json"):
                with open(os.path.join(d, fn), "r", encoding="utf-8") as f:
                    p = json.load(f)
                items.append({"profile_id": p["profile_id"], "subject": p.get("subject"), "version": p.get("version")})
    print(json.dumps({"ok": True, "count": len(items), "items": items}, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description="T9 对手画像")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    sub = ap.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init")
    i.add_argument("--id", required=True)
    i.add_argument("--subject", required=True)
    i.add_argument("--intuition")

    e = sub.add_parser("evidence")
    e.add_argument("--id", required=True)
    e.add_argument("--dim", required=True)
    e.add_argument("--estimate")
    e.add_argument("--direction", choices=["support", "oppose"], default="support")
    e.add_argument("--note")
    e.add_argument("--source", default="user")

    s = sub.add_parser("show")
    s.add_argument("--id", required=True)

    sub.add_parser("list")

    args = ap.parse_args()
    if args.cmd == "init":
        return cmd_init(args, args.dir)
    if args.cmd == "evidence":
        return cmd_evidence(args, args.dir)
    if args.cmd == "show":
        return cmd_show(args, args.dir)
    return cmd_list(args, args.dir)


if __name__ == "__main__":
    sys.exit(main())
