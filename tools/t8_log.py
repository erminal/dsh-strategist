#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T8 日志与复盘（SQLite，标准库）

用法：
    python tools/t8_log.py record  --decision examples/case4/decision.json --session s-001 --structure distribution --goal-type attack
    python tools/t8_log.py outcome --id 1 --result win --note "谈成 10%"
    python tools/t8_log.py list    --limit 10
    python tools/t8_log.py review

默认数据库：data/strategy.db（自动创建）。
定位：记录决策与结果，算命中率与 Brier；不修改历史，只追加/更新结果。
"""

import json
import os
import sys
import sqlite3
import argparse
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(ROOT, "data", "strategy.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  goal_type TEXT,
  structure TEXT
);
CREATE TABLE IF NOT EXISTS decisions (
  decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  conclusion TEXT,
  confidence REAL,
  cards TEXT,
  decision_json TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outcomes (
  decision_id INTEGER PRIMARY KEY,
  result TEXT NOT NULL,
  note TEXT,
  measured_at TEXT NOT NULL
);
"""

RESULT_SCORE = {"win": 1.0, "partial": 0.5, "lose": 0.0}


def connect(db):
    os.makedirs(os.path.dirname(db), exist_ok=True)
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA)
    return conn


def now():
    return datetime.now().isoformat(timespec="seconds")


def cmd_record(args, conn):
    with open(args.decision, "r", encoding="utf-8") as f:
        d = json.load(f)
    conn.execute("INSERT OR IGNORE INTO sessions(session_id, created_at, goal_type, structure) VALUES (?,?,?,?)",
                 (args.session, now(), args.goal_type, args.structure))
    cur = conn.execute(
        "INSERT INTO decisions(session_id, conclusion, confidence, cards, decision_json, created_at) VALUES (?,?,?,?,?,?)",
        (args.session, d.get("conclusion", ""), d.get("confidence"), ",".join(d.get("cards_used", [])),
         json.dumps(d, ensure_ascii=False), now()),
    )
    conn.commit()
    print(json.dumps({"ok": True, "decision_id": cur.lastrowid, "session": args.session}, ensure_ascii=False, indent=2))
    return 0


def cmd_outcome(args, conn):
    row = conn.execute("SELECT decision_id FROM decisions WHERE decision_id=?", (args.id,)).fetchone()
    if not row:
        print(json.dumps({"ok": False, "error": f"decision_id {args.id} 不存在"}, ensure_ascii=False, indent=2))
        return 1
    if args.result not in ("win", "lose", "partial", "unknown", "pending"):
        print(json.dumps({"ok": False, "error": "result 必须是 win/lose/partial/unknown/pending"}, ensure_ascii=False, indent=2))
        return 1
    conn.execute("INSERT OR REPLACE INTO outcomes(decision_id, result, note, measured_at) VALUES (?,?,?,?)",
                 (args.id, args.result, args.note, now()))
    conn.commit()
    print(json.dumps({"ok": True, "decision_id": args.id, "result": args.result}, ensure_ascii=False, indent=2))
    return 0


def cmd_list(args, conn):
    rows = conn.execute(
        "SELECT d.decision_id, d.session_id, d.conclusion, d.confidence, d.cards, d.created_at, o.result "
        "FROM decisions d LEFT JOIN outcomes o ON d.decision_id=o.decision_id "
        "ORDER BY d.decision_id DESC LIMIT ?", (args.limit,)
    ).fetchall()
    items = [{"decision_id": r[0], "session": r[1], "conclusion": r[2], "confidence": r[3],
              "cards": r[4], "created_at": r[5], "result": r[6]} for r in rows]
    print(json.dumps({"ok": True, "count": len(items), "items": items}, ensure_ascii=False, indent=2))
    return 0


def cmd_review(args, conn):
    rows = conn.execute(
        "SELECT d.decision_id, d.confidence, d.cards, o.result FROM decisions d "
        "JOIN outcomes o ON d.decision_id=o.decision_id WHERE o.result IN ('win','lose','partial')"
    ).fetchall()
    if not rows:
        print(json.dumps({"ok": True, "decided": 0, "note": "暂无已定结果的决策"}, ensure_ascii=False, indent=2))
        return 0
    briers, wins = [], 0
    for _did, conf, _cards, result in rows:
        score = RESULT_SCORE[result]
        if result == "win":
            wins += 1
        if conf is not None:
            briers.append((conf - score) ** 2)
    report = {
        "ok": True,
        "decided": len(rows),
        "wins": wins,
        "win_rate": round(wins / len(rows), 3),
        "mean_confidence": round(sum(r[1] for r in rows if r[1] is not None) / max(1, len([r for r in rows if r[1] is not None])), 3),
        "brier": round(sum(briers) / len(briers), 4) if briers else None,
        "note": "Brier 越低越好；置信度未经校准时仅供参考",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description="T8 日志与复盘")
    ap.add_argument("--db", default=DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("record")
    r.add_argument("--decision", required=True)
    r.add_argument("--session", default="s-default")
    r.add_argument("--structure")
    r.add_argument("--goal-type")

    o = sub.add_parser("outcome")
    o.add_argument("--id", type=int, required=True)
    o.add_argument("--result", required=True)
    o.add_argument("--note")

    l = sub.add_parser("list")
    l.add_argument("--limit", type=int, default=10)

    sub.add_parser("review")

    args = ap.parse_args()
    conn = connect(args.db)
    if args.cmd == "record":
        return cmd_record(args, conn)
    if args.cmd == "outcome":
        return cmd_outcome(args, conn)
    if args.cmd == "list":
        return cmd_list(args, conn)
    return cmd_review(args, conn)


if __name__ == "__main__":
    sys.exit(main())
