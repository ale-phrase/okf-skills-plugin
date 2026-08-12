#!/usr/bin/env python3
"""Generate a single self-contained viz.html for an OKF bundle.

The bundle (concepts + link graph) is embedded as JSON; only the Cytoscape and
marked JS libraries load from a CDN. No bundle data leaves the page. Approach
adapted from the Google Cloud knowledge-catalog OKF reference `visualize`
tool (Apache-2.0).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from okf_bundle import LINK, link_target, parse_yaml, read_utf8, rel, split_frontmatter  # noqa: E402

RESERVED = {"index.md", "log.md"}


def build_model(root: Path, name: str) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"bundle is not a directory: {root}")
    concepts: dict[str, dict] = {}
    texts: dict[str, tuple[Path, str]] = {}
    for path in sorted(root.rglob("*.md")):
        if path.name in RESERVED:
            continue
        cid = rel(path, root)[:-3]  # drop ".md"
        try:
            text, _ = read_utf8(path)
        except (OSError, ValueError):
            continue  # unreadable; a validation concern, skip in the viz
        parts = split_frontmatter(text)
        try:
            meta = parse_yaml(parts[0]) if parts else {}
        except Exception:
            meta = {}
        if not isinstance(meta, dict):
            meta = {}
        body = parts[1] if parts else text
        concepts[cid] = {
            "id": cid,
            "title": str(meta.get("title") or cid.rsplit("/", 1)[-1]),
            "type": str(meta.get("type") or "?"),
            "description": str(meta.get("description") or ""),
            "status": meta.get("status"),
            "markdown": body,
        }
        texts[cid] = (path, text)
    edges = set()
    for cid, (path, text) in texts.items():
        for match in LINK.finditer(text):
            target = link_target(path, root, match.group(1))
            if target is None:
                continue
            try:
                tid = target.relative_to(root).as_posix()
            except ValueError:
                continue
            if tid.endswith(".md") and Path(tid).name not in RESERVED:
                tid = tid[:-3]
                if tid in concepts and tid != cid:
                    edges.add((cid, tid))
    return {
        "name": name,
        "concepts": list(concepts.values()),
        "edges": [{"source": s, "target": t} for s, t in sorted(edges)],
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OKF: __OKF_NAME__</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  :root{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#e2e2e2;--accent:#2d6cdf;}
  @media(prefers-color-scheme:dark){:root{--bg:#161616;--fg:#eaeaea;--muted:#9a9a9a;--line:#333;--accent:#6ea8ff;}}
  *{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,sans-serif;color:var(--fg);background:var(--bg);height:100vh;display:flex;flex-direction:column}
  header{padding:8px 14px;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:baseline}
  header b{font-size:15px}header span{color:var(--muted);font-size:12px}
  #main{flex:1;display:flex;min-height:0}
  #graph{flex:1;min-width:0;border-right:1px solid var(--line)}
  #side{width:42%;max-width:620px;overflow:auto;padding:16px 20px}
  #side h1{font-size:18px;margin:0 0 2px}#side .meta{color:var(--muted);font-size:12px;margin-bottom:12px}
  #side pre{background:rgba(127,127,127,.12);padding:10px;border-radius:6px;overflow:auto}
  #side code{background:rgba(127,127,127,.12);padding:1px 4px;border-radius:4px}
  #side a{color:var(--accent)}.empty{color:var(--muted)}
</style></head><body>
<header><b>OKF · __OKF_NAME__</b><span id="stat"></span><span>click a node to read a concept</span></header>
<div id="main"><div id="graph"></div><div id="side"><p class="empty">Select a concept.</p></div></div>
<script id="okf-data" type="application/json">__OKF_DATA__</script>
<script>
const data = JSON.parse(document.getElementById('okf-data').textContent);
const byId = Object.fromEntries(data.concepts.map(c=>[c.id,c]));
document.getElementById('stat').textContent = data.concepts.length+' concepts · '+data.edges.length+' links';
const cy = cytoscape({
  container: document.getElementById('graph'),
  elements: [
    ...data.concepts.map(c=>({data:{id:c.id,label:c.title,type:c.type}})),
    ...data.edges.map(e=>({data:{source:e.source,target:e.target}}))
  ],
  style:[
    {selector:'node',style:{'label':'data(label)','font-size':9,'background-color':'#6ea8ff','text-wrap':'wrap','text-max-width':90,'color':getComputedStyle(document.body).color}},
    {selector:'edge',style:{'width':1,'line-color':'#9993','target-arrow-color':'#9993','target-arrow-shape':'triangle','curve-style':'bezier'}},
    {selector:'node:selected',style:{'background-color':'#2d6cdf'}}
  ],
  layout:{name:'cose',animate:false,padding:20}
});
function show(id){
  const c = byId[id]; const side = document.getElementById('side');
  if(!c){side.innerHTML='<p class="empty">Not found.</p>';return;}
  const meta = [c.type, c.status].filter(Boolean).join(' · ');
  side.innerHTML = '<h1></h1><div class="meta"></div><div id="body"></div>';
  side.querySelector('h1').textContent = c.title;
  side.querySelector('.meta').textContent = meta + '  ' + c.id;
  document.getElementById('body').innerHTML = marked.parse(c.markdown||'');
}
cy.on('tap','node',e=>show(e.target.id()));
</script></body></html>
"""


def render(model: dict) -> str:
    payload = json.dumps(model, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__OKF_NAME__", model["name"]).replace("__OKF_DATA__", payload)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bundle", nargs="?", type=Path)
    ap.add_argument("--out", type=Path, help="output path (default BUNDLE/viz.html)")
    ap.add_argument("--name", help="display name (default bundle dir name)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if args.bundle is None:
        ap.error("bundle is required unless --self-test")
    root = args.bundle.resolve()
    name = args.name or root.name
    try:
        html = render(build_model(root, name))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    out = args.out or (root / "viz.html")
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}")
    return 0


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.md").write_text("---\ntype: Note\ntitle: Alpha\n---\nlinks to [b](./b.md)\n", encoding="utf-8")
        (root / "b.md").write_text("---\ntype: Note\ntitle: Beta\n---\nbody\n", encoding="utf-8")
        model = build_model(root, "t")
        assert len(model["concepts"]) == 2, model
        assert {"source": "a", "target": "b"} in model["edges"], model
        html = render(model)
        assert "Alpha" in html and "okf-data" in html
        assert "</script>" not in json.dumps(model)  # payload escaping sanity
    print("viz self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
