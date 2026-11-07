#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安装 dsh-strategist 技能到 DSH 技能目录（标准库）

用法：
    python tools/install_skill.py --scope user --dry-run
    python tools/install_skill.py --scope user
    python tools/install_skill.py --scope project
    python tools/install_skill.py --target-root <目录>

scope:
    user    -> $DSH_HOME/skills/dsh-strategist（默认 ~/.dsh/skills，rank 400）
    project -> <项目根>/.dsh/skills/dsh-strategist（rank 100，仅本项目会话）
    <dir>   -> <target-root>/dsh-strategist（自定义）

默认 dry-run 关闭；--force 覆盖已存在目录。
"""

import json
import os
import sys
import shutil
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "skills", "dsh-strategist")


def validate():
    skill = os.path.join(SRC, "SKILL.md")
    if not os.path.exists(skill):
        return False, f"缺少 {skill}"
    with open(skill, "r", encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return False, "SKILL.md 缺少 frontmatter"
    head = text.split("---", 2)[1]
    for key in ("name:", "description:"):
        if key not in head:
            return False, f"frontmatter 缺少 {key}"
    return True, "ok"


def target_of(args):
    if args.scope == "user":
        home = os.environ.get("DSH_HOME") or os.path.join(os.path.expanduser("~"), ".dsh")
        return os.path.join(home, "skills", "dsh-strategist"), home
    if args.scope == "project":
        return os.path.join(ROOT, ".dsh", "skills", "dsh-strategist"), ROOT
    if args.target_root:
        return os.path.join(os.path.abspath(args.target_root), "dsh-strategist"), os.path.abspath(args.target_root)
    return None, None


def main():
    ap = argparse.ArgumentParser(description="安装 dsh-strategist 技能")
    ap.add_argument("--scope", choices=["user", "project", "custom"], default="user")
    ap.add_argument("--target-root", help="scope=custom 时的目标根目录")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ok, msg = validate()
    if not ok:
        print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False, indent=2))
        return 1

    dst, base = target_of(args)
    if not dst:
        print(json.dumps({"ok": False, "error": "scope=custom 需要 --target-root"}, ensure_ascii=False, indent=2))
        return 1

    files = []
    for dirpath, _dirs, names in os.walk(SRC):
        for n in names:
            files.append(os.path.relpath(os.path.join(dirpath, n), SRC))

    if os.path.exists(dst) and not args.force:
        print(json.dumps({"ok": False, "error": f"目标已存在：{dst}（用 --force 覆盖）"}, ensure_ascii=False, indent=2))
        return 1

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "src": SRC, "dst": dst,
                          "files": files, "note": "未写入；去掉 --dry-run 执行安装"},
                         ensure_ascii=False, indent=2))
        return 0

    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copytree(SRC, dst)
    # 写入本地项目根，供技能在用户级安装时定位 tools/kb（不进入产品源文件）
    root_note = os.path.join(dst, "project-root.txt")
    with open(root_note, "w", encoding="utf-8") as f:
        f.write(os.path.abspath(ROOT) + "\n")
    print(json.dumps({
        "ok": True, "src": SRC, "dst": dst, "file_count": len(files) + 1,
        "project_root": os.path.abspath(ROOT),
        "note": "已写入 project-root.txt；DSH 技能目录会被监听，若未立即出现请重开会话或重启 DSH。",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
