#!/usr/bin/env python3
"""Generate the static, accessible notebook gallery served at /services/demos/.

The gallery is the anonymous landing page, modelled on a Colab welcome page: it explains how the
browser runtime works and lists each notebook with a one-click "Open" link into JupyterLite.
Titles and summaries come from the first Markdown cell of every notebook, so the page can never
drift from the bundled catalog. Usage: build_gallery.py <notebook-dir> <output-html>.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

SECTIONS = [
    (1, 10, "Getting started with the meteo@uniparthenope API",
     "Catalogs, places, forecasts, and map layers."),
    (11, 15, "Numerical models", "WRF, WaveWatch III, ROMS, and WaComM products."),
    (16, 20, "Live weather-station network", "Observations from the meteo@uniparthenope instruments."),
    (21, 30, "Transparent artificial intelligence",
     "Small, inspectable models trained on public data — educational, not operational."),
]


def describe(path: Path) -> tuple[str, str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        lines = [line.strip() for line in "".join(cell.get("source", [])).splitlines()]
        title = next((line.lstrip("# ") for line in lines if line.startswith("#")), path.stem)
        summary = next((line for line in lines if line and not line.startswith("#")), "")
        return title, summary
    return path.stem, ""


def card(path: Path) -> str:
    title, summary = describe(path)
    number = path.name.split("_", 1)[0]
    href = f"lab/index.html?path={html.escape(path.name)}"
    return (
        '<li class="nb-card">'
        f'<span class="nb-num" aria-hidden="true">{html.escape(number)}</span>'
        f'<h3><a href="{href}">{html.escape(title)}</a></h3>'
        f"<p>{html.escape(summary)}</p>"
        f'<span class="nb-file">{html.escape(path.name)}</span>'
        "</li>"
    )


def build(notebook_dir: Path) -> str:
    notebooks = sorted(notebook_dir.glob("[0-9][0-9]_*.ipynb"))
    sections = []
    for first, last, heading, blurb in SECTIONS:
        items = [nb for nb in notebooks if first <= int(nb.name[:2]) <= last]
        if not items:
            continue
        anchor = f"s{first:02d}"
        sections.append(
            f'<section aria-labelledby="{anchor}"><h2 id="{anchor}">{html.escape(heading)}</h2>'
            f'<p class="muted">{html.escape(blurb)}</p><ul class="nb-grid">'
            + "".join(card(nb) for nb in items)
            + "</ul></section>"
        )
    return TEMPLATE.replace("{{COUNT}}", str(len(notebooks))).replace("{{SECTIONS}}", "".join(sections))


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#1f4e79">
<meta name="description" content="Run meteo@uniparthenope weather, ocean, and sensor notebooks in your browser.">
<title>Notebook gallery · lab.meteo@uniparthenope</title>
<link rel="icon" href="/services/demos/lab-meteo-logo.png" type="image/png">
<style>
:root { --primary:#1f4e79; --secondary:#2a91eb; --accent:#181c63; --page:#f4f7fa; --surface:#fff;
  --ink:#13283a; --muted:#55687a; --link:#1f4e79; --line:#dbe3ea; --radius:1rem;
  --shadow:0 .75rem 2.5rem rgba(5,37,63,.09); }
@media (prefers-color-scheme: dark) { :root { --page:#0c1822; --surface:#142433; --ink:#edf6fb;
  --muted:#a9bdca; --link:#7cc0ff; --line:#27394a; --shadow:0 .75rem 2.5rem rgba(0,0,0,.24); } }
* { box-sizing:border-box; }
body { margin:0; min-height:100vh; display:flex; flex-direction:column; background:var(--page); color:var(--ink);
  font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Open Sans",sans-serif; }
a { color:var(--link); text-underline-offset:.15em; }
:where(a,button):focus-visible { outline:3px solid color-mix(in srgb,var(--secondary) 70%,#000); outline-offset:3px; }
.skip { position:fixed; left:1rem; top:-5rem; z-index:9; padding:.65rem 1rem; border-radius:.5rem; background:#fff; color:#111; font-weight:600; }
.skip:focus { top:1rem; }
header { background:linear-gradient(120deg,var(--primary),var(--accent)); color:#fff; box-shadow:0 .25rem 1.5rem rgba(0,26,48,.2); }
.bar { max-width:1280px; margin:0 auto; padding:.6rem 1rem; display:flex; flex-wrap:wrap; align-items:center; gap:.75rem 1.25rem; }
.brand { display:flex; align-items:center; gap:.7rem; color:#fff; text-decoration:none; margin-right:auto; }
.brand img { width:2.5rem; height:2.5rem; border-radius:50%; background:#fff; padding:.1rem; }
.brand strong, .brand small { display:block; line-height:1.1; }
.brand small { font-size:.7rem; opacity:.85; margin-top:.2rem; letter-spacing:.035em; }
header nav a { color:rgba(255,255,255,.92); text-decoration:none; padding:.4rem .6rem; border-radius:.5rem; }
header nav a:hover, header nav a:focus { background:rgba(255,255,255,.12); color:#fff; }
header nav .signin { background:#fff; color:var(--primary); font-weight:700; }
main { flex:1 0 auto; }
.shell { max-width:1280px; margin:0 auto; padding:clamp(1rem,2.5vw,2rem); }
.hero { display:grid; grid-template-columns:minmax(0,1.6fr) minmax(0,1fr); gap:1.5rem; align-items:center; padding-block:1.5rem 2rem; }
@media (max-width:860px) { .hero { grid-template-columns:1fr; } }
.kicker { color:var(--link); text-transform:uppercase; letter-spacing:.12em; font-weight:800; font-size:.72rem; }
h1 { font-size:clamp(2rem,4.5vw,3.1rem); letter-spacing:-.035em; line-height:1.1; margin:.4rem 0 1rem; }
.lead { font-size:1.15rem; color:var(--muted); max-width:44rem; }
.actions { display:flex; flex-wrap:wrap; gap:.6rem; margin-top:1.25rem; }
.btn { display:inline-block; padding:.7rem 1.15rem; border-radius:.65rem; font-weight:600; text-decoration:none; border:2px solid var(--primary); }
.btn-primary { background:var(--primary); color:#fff; }
.btn-primary:hover { background:var(--accent); border-color:var(--accent); color:#fff; }
.btn-outline { color:var(--link); border-color:var(--link); }
.panel { background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); padding:1.25rem 1.5rem; }
.panel h2 { font-size:1.05rem; margin:0 0 .6rem; }
.panel ol { margin:0; padding-left:1.2rem; color:var(--muted); }
.panel li { margin-bottom:.35rem; }
section { margin-top:2rem; }
section h2 { font-size:1.45rem; letter-spacing:-.02em; margin:0 0 .2rem; }
.muted { color:var(--muted); margin:0 0 1rem; }
.nb-grid { list-style:none; margin:0; padding:0; display:grid; grid-template-columns:repeat(auto-fill,minmax(16rem,1fr)); gap:1rem; }
.nb-card { position:relative; background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); padding:1.1rem 1.2rem 2.4rem; }
.nb-card:focus-within, .nb-card:hover { border-color:var(--secondary); }
.nb-card h3 { font-size:1.02rem; margin:.35rem 0 .4rem; }
.nb-card h3 a { text-decoration:none; }
.nb-card h3 a::after { content:""; position:absolute; inset:0; border-radius:var(--radius); }
.nb-card p { margin:0; color:var(--muted); font-size:.92rem; }
.nb-num { display:inline-grid; place-items:center; min-width:2rem; height:2rem; border-radius:.55rem; font-weight:800; font-size:.85rem;
  background:color-mix(in srgb,var(--secondary) 18%,transparent); color:var(--ink); }
.nb-file { position:absolute; left:1.2rem; bottom:.8rem; font:.75rem ui-monospace,Menlo,Consolas,monospace; color:var(--muted); }
footer { margin-top:3rem; color:var(--muted); border-top:1px solid var(--line); background:color-mix(in srgb,var(--surface) 92%,var(--primary)); }
footer .shell { display:flex; flex-wrap:wrap; justify-content:space-between; gap:1rem; padding-block:1.5rem; }
footer a { color:inherit; margin-right:1rem; }
@media (prefers-reduced-motion: reduce) { * { transition:none !important; scroll-behavior:auto !important; } }
</style>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<header>
  <div class="bar">
    <a class="brand" href="/services/demos/"><img src="/services/demos/lab-meteo-logo.png" alt="">
      <span><strong>lab.meteo@uniparthenope</strong><small>Weather and marine data workspace</small></span></a>
    <nav aria-label="Main navigation">
      <a href="lab/index.html">Notebook lab</a>
      <a href="https://meteo.uniparthenope.it" rel="noopener">Forecasts</a>
      <a href="https://network.meteo.uniparthenope.it" rel="noopener">Sensor network</a>
      <a class="signin" href="/hub/login">Sign in</a>
    </nav>
  </div>
</header>
<main id="main" tabindex="-1">
  <div class="shell">
    <div class="hero">
      <div>
        <div class="kicker">Interactive notebooks · no installation</div>
        <h1>Weather, sea, and sensor data, ready to run in your browser.</h1>
        <p class="lead">Open any of the {{COUNT}} meteo@uniparthenope notebooks, edit the code, and run it
          immediately. Python executes inside your browser; nothing you type is sent to our servers.</p>
        <div class="actions">
          <a class="btn btn-primary" href="lab/index.html?path=01_api_catalog.ipynb">Open the first notebook</a>
          <a class="btn btn-outline" href="lab/index.html">Open the notebook lab</a>
          <a class="btn btn-outline" href="/hub/login">Sign in for a server runtime</a>
        </div>
      </div>
      <aside class="panel" aria-labelledby="how">
        <h2 id="how">How it works</h2>
        <ol>
          <li>Choose a notebook below; it opens in the browser lab.</li>
          <li>Run cells with <kbd>Shift</kbd>+<kbd>Enter</kbd>; the first run loads the Python runtime.</li>
          <li>Your edits stay in this browser. Use <em>File → Download</em> to keep a copy.</li>
          <li>Signed-in members get a persistent JupyterLab server with read-only access to the
            model archive and the station network.</li>
        </ol>
      </aside>
    </div>
    {{SECTIONS}}
  </div>
</main>
<footer>
  <div class="shell">
    <div><strong>lab.meteo@uniparthenope</strong><br><span>Forecasts are generated automatically and are
      not official warnings. Times are UTC.</span></div>
    <nav aria-label="Legal and related links">
      <a href="/hub/lab/privacy">Privacy &amp; data protection</a>
      <a href="/hub/lab/accessibility">Accessibility</a>
      <a href="https://meteo.uniparthenope.it" rel="noopener">meteo@uniparthenope</a>
    </nav>
  </div>
</footer>
</body>
</html>
"""


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_gallery.py <notebook-dir> <output-html>")
    Path(sys.argv[2]).write_text(build(Path(sys.argv[1])), encoding="utf-8")


if __name__ == "__main__":
    main()
