import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples" / "demo"


def build(tmp_path):
    out = tmp_path / "demo.html"
    subprocess.run([sys.executable, str(ROOT / "build.py"), "--data", str(DATA), "--out", str(out)],
                   check=True, capture_output=True, text=True)
    return out.read_text(encoding="utf-8")


def test_build_replaces_placeholder(tmp_path):
    html = build(tmp_path)
    assert "__TOPOLOGY_DATA__ ||" not in html
    assert "阿岚" in html and "苏禾" in html


def test_node_and_edge_counts(tmp_path):
    roster = json.loads((DATA / "roster.json").read_text(encoding="utf-8"))
    html = build(tmp_path)
    for p in roster["people"]:
        assert f'"name":"{p["name"]}"' in html.replace(" ", "")
    for e in roster["peer_edges"]:
        assert e["a"] in html and e["b"] in html


def test_stage_ids_are_known(tmp_path):
    roster = json.loads((DATA / "roster.json").read_text(encoding="utf-8"))
    ids = {s["id"] for s in roster["stages"]}
    for p in roster["people"]:
        assert p["stage"] in ids, f'{p["name"]} 的阶段 {p["stage"]} 未定义'


def test_no_real_data_committed():
    """示例数据必须是虚构的：检查 demo 目录不含常见真实标识。"""
    blob = "".join(p.read_text(encoding="utf-8", errors="ignore")
                   for p in (DATA.rglob("*")) if p.is_file())
    import re
    assert not re.search(r"1[3-9]\d{9}", blob), "示例数据疑似含真实手机号"
    for banned in ("@163.com", "@gmail.com", "@qq.com"):
        assert banned not in blob, f"示例数据疑似含真实信息：{banned}"
