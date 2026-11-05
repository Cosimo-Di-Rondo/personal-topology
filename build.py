#!/usr/bin/env python3
"""personal-topology build: data/ -> 单文件 HTML

用法：
    python3 build.py --data examples/demo --out examples/demo.html

数据目录约定：
    data/roster.json          # 中心节点、阶段、人物、圈子、人际连线
    data/people/<名字>.md      # 每个人的档案（事实区会被抽成口述记录）

只依赖标准库。产物是零外部依赖的单文件 HTML，双击即可打开。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "template" / "index.html"
PLACEHOLDER = "window.__TOPOLOGY_DATA__ ||"


def parse_person_md(path: Path) -> dict:
    """从人物档案 md 抽字段与事实区。宽容解析，缺字段不报错。"""
    text = path.read_text(encoding="utf-8")
    meta = {}
    for line in text.splitlines():
        m = re.match(r"^-\s*([^：:]{1,12})[：:]\s*(.*)$", line.strip())
        if m and m.group(1) not in meta:
            meta[m.group(1).strip()] = m.group(2).strip()

    facts = []
    if "<!-- 事实区:start -->" in text:
        body = text.split("<!-- 事实区:start -->")[1].split("<!-- 事实区:end -->")[0]
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("- "):
                item = line[2:].strip()
                if item and not item.startswith("待补"):
                    facts.append(item)

    return {
        "name": meta.get("别名") if meta.get("别名") not in (None, "—", "-") else path.stem,
        "tags": [t.strip() for t in re.split(r"[、,，/]", meta.get("标签", "")) if t.strip()],
        "relation": meta.get("关系", ""),
        "stage": meta.get("阶段", ""),
        "count": int(re.sub(r"\D", "", meta.get("出现次数", "0")) or 0),
        "facts": facts,
        "file": str(path.name),
    }


def load_data(data_dir: Path) -> dict:
    roster_path = data_dir / "roster.json"
    if not roster_path.exists():
        sys.exit(f"找不到 {roster_path}")
    roster = json.loads(roster_path.read_text(encoding="utf-8"))

    people_dir = data_dir / "people"
    if people_dir.exists():
        by_name = {}
        for md in sorted(people_dir.glob("*.md")):
            p = parse_person_md(md)
            by_name[md.stem] = p
            by_name[p["name"]] = p
        for person in roster.get("people", []):
            extra = by_name.get(person.get("name", "")) or by_name.get(person.get("file", "").removesuffix(".md"))
            if extra:
                for k in ("facts", "tags", "file"):
                    if not person.get(k):
                        person[k] = extra[k]
                person.setdefault("relation", extra["relation"])
                person.setdefault("stage", extra["stage"])
                if not person.get("count"):
                    person["count"] = extra["count"]
    return roster


def build(data_dir: Path, out_path: Path) -> Path:
    data = load_data(data_dir)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8")
    # 模板里是 `const DATA = window.__TOPOLOGY_DATA__ || {默认};` -> 整句换成真实数据
    pattern = re.compile(r"const DATA = window\.__TOPOLOGY_DATA__ \|\| \{.*?\};", re.S)
    if not pattern.search(html):
        raise SystemExit("模板缺少 DATA 注入点")
    html = pattern.sub(lambda _m: "const DATA = " + payload + " || {};", html, count=1)

    names = {p["name"] for p in data.get("people", [])}
    for e in data.get("peer_edges", []):
        for side in ("a", "b"):
            if e[side] not in names and e[side] != data.get("self", {}).get("name"):
                raise SystemExit(f"人际连线引用了不存在的人：{e[side]}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"✓ 生成 {out_path}（{len(data.get('people', []))} 人 / "
          f"{len(data.get('peer_edges', []))} 条人际线 / {out_path.stat().st_size // 1024} KB）")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="把个人档案渲染成单文件人际拓扑 HTML")
    ap.add_argument("--data", required=True, help="数据目录（含 roster.json 与 people/）")
    ap.add_argument("--out", required=True, help="输出 HTML 路径")
    args = ap.parse_args()
    build(Path(args.data), Path(args.out))


if __name__ == "__main__":
    main()
