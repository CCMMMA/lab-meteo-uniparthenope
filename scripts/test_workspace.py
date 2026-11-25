#!/usr/bin/env python3
"""Tests for the Colab-style workspace helpers; they need JupyterHub, so run them in the Hub image:

    docker compose build jupyterhub
    docker run --rm -v "$PWD/scripts:/scripts:ro" --entrypoint python \
      lab-meteo-uniparthenope-jupyterhub /scripts/test_workspace.py
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/srv/jupyterhub")

from tornado import web  # noqa: E402

from lab_ext.workspace import GITHUB_PATH, parse_github_url, safe_segments, validate_notebook  # noqa: E402


def raises(fn, *args) -> bool:
    try:
        fn(*args)
    except web.HTTPError:
        return True
    return False


def main() -> None:
    assert parse_github_url("https://github.com/o/r/blob/main/a/b.ipynb") == "o/r/blob/main/a/b.ipynb"
    assert parse_github_url("https://raw.githubusercontent.com/o/r/v1.0/x.ipynb") == "o/r/blob/v1.0/x.ipynb"
    for bad in ("https://example.org/o/r/blob/main/x.ipynb", "file:///etc/passwd",
                "https://github.com/o/r/tree/main/x", "https://github.com/o/r/blob/main/x.py"):
        assert raises(parse_github_url, bad), bad
    assert GITHUB_PATH.match("CCMMMA/lab-meteo-uniparthenope/blob/main/demos/01_api_catalog.ipynb")
    assert safe_segments("demos/01 a (copy).ipynb") == ["demos", "01 a (copy).ipynb"]
    for bad in ("../x.ipynb", "a/../../x.ipynb", ".hidden/x.ipynb", "a/<b>.ipynb"):
        assert raises(safe_segments, bad), bad
    good = json.dumps({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}).encode()
    assert validate_notebook(good)["nbformat"] == 4
    for bad in (b"not json", b"[]", json.dumps({"cells": [], "nbformat": 3}).encode(), b"\xff\xfe"):
        assert raises(validate_notebook, bad), bad
    print("workspace tests passed")


if __name__ == "__main__":
    main()
