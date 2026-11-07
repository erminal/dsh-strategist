#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地可视化：把案例渲染成一份自包含 HTML（无外部依赖）

用法：
    python tools/render_report.py --case examples/case4 --out examples/case4/report.html
    python tools/render_report.py --case examples/case4 --out examples/case4/report.html

内容：目标卡、SIR 概览、T3 检索、T5 期望值、T6 分支树、决策卡、T10 法律、T11 心性、校验状态。
"""

import json
import os
import sys
import html
import subprocess
import argparse
import tempfile
import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def esc(v):
    return html.escape(str(v if v is not None else ""))


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_json(script, args):
    fd, path = tempfile.mkstemp(suffix=".json", prefix="render_")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as f:
            subprocess.run([PY, os.path.join(ROOT, "tools", script)] + args,
                           stdout=f, stderr=subprocess.STDOUT)
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read().strip()
        return json.loads(txt) if txt.startswith("{") else None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


BADGE = {"red": "badge-red", "orange": "badge-orange", "yellow": "badge-yellow",
         "green": "badge-green", "win": "badge-green", "lose": "badge-red"}


def badge(level):
    return f'<span class="badge {BADGE.get(str(level), "badge-gray")}">{esc(level)}</span>'


def tree_html(tree):
    nodes = {n["id"]: n for n in tree.get("nodes", [])}
    children = {}
    for e in tree.get("edges", []):
        children.setdefault(e["from"], []).append(e["to"])

    def render(nid):
        n = nodes.get(nid, {})
        label = esc(n.get("label", nid))
        extra = ""
        if n.get("type") == "reaction":
            extra = f'<span class="muted">概率 {esc(n.get("prob"))} · 收益 {esc(n.get("payoff"))} · {esc(n.get("source"))}</span>'
        kids = children.get(nid, [])
        inner = "".join(render(k) for k in kids)
        return f'<li><span class="node {esc(n.get("type"))}">{label}</span> {extra}{("<ul>" + inner + "</ul>") if inner else ""}</li>'

    roots = [n["id"] for n in tree.get("nodes", []) if not any(e["to"] == n["id"] for e in tree.get("edges", []))]
    return "<ul class='tree'>" + "".join(render(r) for r in roots) + "</ul>"


def main():
    ap = argparse.ArgumentParser(description="渲染本地 HTML 报告")
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    case = os.path.abspath(args.case)
    p = lambda rel: os.path.join(case, rel)

    bg = ""
    if os.path.exists(p("background.txt")):
        with open(p("background.txt"), "r", encoding="utf-8") as f:
            bg = f.read().strip()

    goal = read_json(p("goal.json"))
    sir = read_json(p("sir.json"))
    decision = read_json(p("decision.json"))
    game_input = read_json(p("game_input.json"))

    t2 = run_json("t2_tag.py", [p("background.txt")]) if bg else None
    t3 = run_json("t3_retrieve.py", [p("sir.json"), "--top-k", "5"]) if sir else None
    t5 = run_json("t5_solve.py", ["expected", "--plans", p("plans.json")]) if os.path.exists(p("plans.json")) else None
    t10 = run_json("t10_legal.py", ["--text", bg]) if bg else None
    t11 = run_json("t11_mind.py", ["--text", bg]) if bg else None
    goal_check = run_json("check.py", ["goal", p("goal.json")]) if goal else None
    sir_check = run_json("check.py", ["sir", p("sir.json")]) if sir else None
    dec_check = run_json("check.py", ["decision", p("decision.json")]) if decision else None

    tmp = tempfile.mkdtemp(prefix="render_")
    game_spec = os.path.join(tmp, "game_spec.json")
    t6 = None
    if game_input and sir:
        cmd = [PY, os.path.join(ROOT, "tools", "t4_build.py"), "--sir", p("sir.json"),
               "--me-actions", "|".join(game_input.get("me_actions", [])),
               "--opp-actions", "|".join(game_input.get("opp_actions", [])), "--out", game_spec]
        run_json("t4_build.py", ["--sir", p("sir.json"),
                                 "--me-actions", "|".join(game_input.get("me_actions", [])),
                                 "--opp-actions", "|".join(game_input.get("opp_actions", [])),
                                 "--out", game_spec])
        if os.path.exists(game_spec) and os.path.exists(p("tree_spec.json")):
            t6 = run_json("t6_tree.py", ["--game", game_spec, "--tree", p("tree_spec.json")])

    structure = (sir or {}).get("structure") or {}
    tags = (sir or {}).get("tags") or {}

    parts = []
    parts.append(f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>军师报告 · {esc(os.path.basename(case))}</title>
<style>
:root {{ --bg:#f6f7f9; --card:#fff; --line:#e5e7eb; --text:#1f2937; --muted:#6b7280; --accent:#2563eb; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; line-height:1.65; }}
.wrap {{ max-width:1040px; margin:0 auto; padding:28px 18px 60px; }}
header {{ margin-bottom:20px; }}
h1 {{ font-size:24px; margin:0 0 6px; }}
.muted {{ color:var(--muted); font-size:13px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px 18px; margin:14px 0; }}
.card h2 {{ font-size:16px; margin:0 0 10px; padding-bottom:8px; border-bottom:1px solid var(--line); }}
.kv {{ display:flex; gap:8px; flex-wrap:wrap; font-size:14px; }}
.kv b {{ color:var(--muted); font-weight:500; }}
.badge {{ display:inline-block; padding:1px 8px; border-radius:999px; font-size:12px; font-weight:600; }}
.badge-red {{ background:#fee2e2; color:#991b1b; }}
.badge-orange {{ background:#ffedd5; color:#9a3412; }}
.badge-yellow {{ background:#fef9c3; color:#854d0e; }}
.badge-green {{ background:#dcfce7; color:#166534; }}
.badge-gray {{ background:#f3f4f6; color:#374151; }}
.scorebar {{ background:#eef2ff; border-radius:6px; height:8px; overflow:hidden; margin-top:6px; }}
.scorebar > i {{ display:block; height:100%; background:var(--accent); }}
.item {{ border:1px solid var(--line); border-radius:10px; padding:10px 12px; margin:8px 0; }}
.item .name {{ font-weight:600; }}
table {{ width:100%; border-collapse:collapse; font-size:14px; }}
th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); }}
th {{ color:var(--muted); font-weight:500; }}
tr.best td {{ background:#eff6ff; font-weight:600; }}
.tree, .tree ul {{ list-style:none; margin:4px 0 4px 18px; padding-left:10px; border-left:1px dashed var(--line); }}
.tree {{ margin-left:0; border-left:none; }}
.node {{ display:inline-block; padding:2px 8px; border-radius:6px; font-size:13px; }}
.node.decision {{ background:#e0e7ff; }}
.node.action {{ background:#dbeafe; }}
.node.reaction {{ background:#f3f4f6; }}
ol, ul {{ margin:6px 0; padding-left:22px; }}
li {{ margin:4px 0; }}
details {{ margin-top:8px; }}
summary {{ cursor:pointer; color:var(--accent); font-size:13px; }}
footer {{ margin-top:24px; color:var(--muted); font-size:12px; }}
</style></head><body><div class="wrap">""")

    parts.append(f"<header><h1>军师报告 · {esc(os.path.basename(case))}</h1>"
                 f"<div class='muted'>生成时间 {esc(datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))} · 本地离线 · 仅供决策参考</div></header>")

    # 概览
    parts.append("<div class='card'><h2>概览</h2><div class='kv'>"
                 f"<span><b>结构</b> {esc(structure.get('primary'))} / {esc(structure.get('secondary'))}</span>"
                 f"<span><b>目的类型</b> {esc((sir or {}).get('goal', {}).get('type'))}</span>"
                 f"<span><b>完备度</b> {esc((sir or {}).get('completeness', {}).get('score'))}</span>"
                 f"<span><b>决策置信</b> {esc((decision or {}).get('confidence'))}</span></div>"
                 f"<div class='kv' style='margin-top:8px'><span><b>标签</b> "
                 + " · ".join(f"{esc(k)}={esc(v)}" for k, v in tags.items()) + "</span></div></div>")

    # 目标
    if goal:
        ul = "".join(f"<li>{esc(x)}</li>" for x in goal.get("success_criteria", []))
        nl = "".join(f"<li>{esc(x)}</li>" for x in goal.get("unacceptable", []))
        parts.append("<div class='card'><h2>目标卡（T0）</h2>"
                     f"<p><b>终极目的</b>：{esc(goal.get('ultimate'))}</p>"
                     f"<p><b>直接目的</b>：{esc(goal.get('direct'))}</p>"
                     f"<div class='grid'><div><b>成功判据</b><ul>{ul}</ul></div>"
                     f"<div><b>失败/不可接受</b><ul>{nl}</ul></div></div>"
                     f"<p class='muted'>关系预算 {esc(goal.get('relationship_budget'))} · 时间窗口 {esc(goal.get('time_window'))}</p></div>")

    # T2
    if t2:
        parts.append("<div class='card'><h2>T2 结构与标签（规则）</h2>"
                     f"<p>主结构 <b>{esc(t2['structure']['primary'])}</b>，次结构 {esc(t2['structure']['secondary'])}"
                     f" <span class='muted'>（置信 {esc(t2['structure'].get('confidence'))}）</span></p>"
                     f"<p class='muted'>规则命中：{esc(', '.join(h['keyword'] for h in t2.get('rule_hits', [])[:12]))}</p></div>")

    # T3
    if t3 and t3.get("results"):
        maxs = max(r["score"] for r in t3["results"]) or 1
        items = []
        for r in t3["results"]:
            pct = int(round(100 * r["score"] / maxs))
            ps = "、".join(r.get("principles", [])[:4])
            items.append(f"<div class='item'><div class='name'>{esc(r['name'])} "
                         f"<span class='muted'>{esc(r['variant_id'])} · {esc((r.get('mechanism') or {}).get('primary'))} · 分数 {esc(r['score'])}</span></div>"
                         f"<div class='scorebar'><i style='width:{pct}%'></i></div>"
                         f"<div class='muted'>原则：{esc(ps) or '—'}</div>"
                         f"<details><summary>命中理由</summary><ul>{''.join('<li>' + esc(w) + '</li>' for w in r.get('why', []))}</ul></details></div>")
        parts.append("<div class='card'><h2>T3 检索结果</h2>" + "".join(items) + "</div>")

    # T5
    if t5 and t5.get("results"):
        rows = []
        for r in t5["results"]:
            cls = " class='best'" if r["plan"] == t5.get("best_plan") else ""
            rows.append(f"<tr{cls}><td>{esc(r['plan'])}</td><td>{esc(r['result'])}</td><td class='muted'>{esc(r.get('formula'))}</td></tr>")
        parts.append("<div class='card'><h2>T5 期望值</h2>"
                     f"<p>最优方案：<b>{esc(t5.get('best_plan'))}</b></p>"
                     "<table><tr><th>方案</th><th>期望值</th><th>公式</th></tr>" + "".join(rows) + "</table>"
                     "<p class='muted'>概率与收益为假设，未经校准。</p></div>")

    # T6
    if t6:
        parts.append("<div class='card'><h2>T6 分支树</h2>"
                     f"<p class='muted'>节点 {esc(t6.get('checks', {}).get('node_count'))} · 概率归一 {esc(t6.get('checks', {}).get('prob_sum_ok'))}</p>"
                     + tree_html(t6)
                     + (f"<p class='muted'>警告：{esc('；'.join(t6.get('warnings', [])))}</p>" if t6.get("warnings") else "")
                     + "</div>")

    # 决策卡
    if decision:
        steps = "".join(f"<li>{esc(s)}</li>" for s in decision.get("steps", []))
        cms = "".join(f"<li>{esc(s)}</li>" for s in decision.get("countermeasures", []))
        parts.append("<div class='card'><h2>决策卡（T7）</h2>"
                     f"<p><b>结论</b>：{esc(decision.get('conclusion'))}</p>"
                     f"<div class='grid'><div><b>步骤</b><ol>{steps}</ol></div>"
                     f"<div><b>反制</b><ul>{cms}</ul></div></div>"
                     f"<p><b>失败判据</b>：{esc(decision.get('fail_criteria'))}</p>"
                     f"<p><b>Plan B</b>：{esc(decision.get('plan_b'))}</p>"
                     f"<p class='kv'><span>伦理 {badge((decision.get('ethics_check') or {}).get('level'))}</span>"
                     f"<span>法律 {badge((decision.get('legal_check') or {}).get('level'))}</span></p>"
                     f"<p class='muted'>来源：{esc('；'.join(decision.get('sources', [])))}</p></div>")

    # T10
    if t10:
        risks = t10.get("risks", [])
        rows = "".join(f"<tr><td>{badge(r.get('level'))}</td><td>{esc(r.get('issue'))}</td><td>{esc(r.get('alternative'))}</td></tr>" for r in risks)
        parts.append("<div class='card'><h2>T10 法律风险</h2>"
                     f"<p>最高等级：{badge(t10.get('highest_level'))} · 是否拦截：{esc(t10.get('blocked'))}</p>"
                     "<table><tr><th>等级</th><th>问题</th><th>合法替代</th></tr>" + rows + "</table>"
                     f"<p class='muted'>{esc(t10.get('disclaimer'))}</p></div>")

    # T11
    if t11:
        ss = t11.get("self_state", {})
        mc = t11.get("mindset_card", {})
        acts = "".join(f"<li>{esc(a)}</li>" for a in mc.get("actions", []))
        parts.append("<div class='card'><h2>T11 心性</h2>"
                     f"<p>情绪 {esc(ss.get('emotion_intensity'))}/5 · 压力 {esc(ss.get('stress'))}/5 · 暂停 {esc(mc.get('pause'))}</p>"
                     f"<p><b>心法</b>：{esc(mc.get('anchor'))}</p><ul>{acts}</ul>"
                     f"<p class='muted'>{esc(t11.get('note'))}</p></div>")

    # 校验
    def chk(name, data):
        if not data:
            return f"<span class='muted'>{name} 无数据</span>"
        return f"{name}：{'✅ 通过' if data.get('ok') else '❌ 未通过'}"
    parts.append("<div class='card'><h2>校验</h2><p class='kv'>"
                 f"<span>{chk('T0', goal_check)}</span><span>{chk('T1', sir_check)}</span><span>{chk('T7', dec_check)}</span>"
                 "</p></div>")

    parts.append("<footer>由 dsh-strategist 本地渲染 · 数字与概率为假设，请以现实判断为准。</footer></div></body></html>")

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    print(json.dumps({"ok": True, "out": out, "size": os.path.getsize(out)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
