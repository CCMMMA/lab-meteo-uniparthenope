#!/usr/bin/env python3
"""Run repository checks that do not require network access or scientific input data."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)
    print(f"FAIL: {message}", file=sys.stderr)


def validate_notebooks() -> None:
    demo_paths = sorted(ROOT.glob("demos/*.ipynb"))
    if len(demo_paths) != 20:
        fail(f"expected 20 public demo notebooks, found {len(demo_paths)}")
    paths = sorted((*ROOT.glob("notebooks/*.ipynb"), *ROOT.glob("templates/*.ipynb"), *demo_paths))
    for path in paths:
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"{path.relative_to(ROOT)} is not valid JSON: {exc}")
            continue
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            if cell.get("cell_type") != "code":
                continue
            if path.parent.name == "demos":
                if cell.get("execution_count") is not None or cell.get("outputs"):
                    fail(f"{path.relative_to(ROOT)} code cell {index} contains transient output")
            source = "".join(cell.get("source", []))
            if not source.strip() or source.lstrip().startswith(("%", "!")):
                continue
            try:
                ast.parse(source, filename=f"{path}:cell-{index}")
            except SyntaxError as exc:
                fail(f"{path.relative_to(ROOT)} code cell {index}: {exc.msg} (line {exc.lineno})")


def validate_markdown_links() -> None:
    link_pattern = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
    for path in sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md", ROOT / "AGENTS.md"]:
        text = path.read_text(encoding="utf-8")
        for target in link_pattern.findall(text):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                fail(f"{path.relative_to(ROOT)} has a broken link to {target}")


def validate_english() -> None:
    italian_markers = re.compile(
        r"\b(?:atteso|città|configurazione|dati|esito|modello|ottenuto|risultati|utente|vento)\b",
        re.IGNORECASE,
    )
    paths = [ROOT / "README.md", ROOT / "AGENTS.md", *(ROOT / "docs").glob("*.md")]
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if italian_markers.search(line):
                fail(f"possible untranslated text in {path.relative_to(ROOT)}:{number}")


def validate_executables() -> None:
    for path in (ROOT / "scripts").iterdir():
        if path.suffix in {".py", ".sh"} and not path.stat().st_mode & 0o111:
            fail(f"{path.relative_to(ROOT)} is not executable")


def validate_compose() -> None:
    try:
        subprocess.run(
            ["docker", "compose", "config", "--quiet"], cwd=ROOT, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
    except FileNotFoundError:
        print("SKIP: Docker CLI is unavailable; Compose validation was not run")
    except subprocess.CalledProcessError as exc:
        fail(f"Docker Compose configuration is invalid: {exc.stderr.strip()}")


validate_notebooks()
validate_markdown_links()
validate_english()
validate_executables()
validate_compose()

if failures:
    print(f"\n{len(failures)} validation failure(s)", file=sys.stderr)
    raise SystemExit(1)
print("Repository validation passed")
