#!/usr/bin/env python3
"""Measure JupyterLab server startup time through the JupyterHub REST API.

Run on the host with an administrator token generated at /hub/token:
    export JUPYTERHUB_TOKEN=...            # administrator token
    python3 scripts/measure_spawn.py --users 1 --runs 5      # single user, 5 runs
    python3 scripts/measure_spawn.py --users 5 --runs 3      # 5 concurrent users

For every run, create missing bench01..benchNN users, start their servers in parallel,
measure time to readiness, and stop them. Output is a CSV file plus a summary.
Only the Python standard library is required.
"""
import argparse
import csv
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ap = argparse.ArgumentParser()
ap.add_argument("--hub", default="http://127.0.0.1:8000")
ap.add_argument("--users", type=int, default=1)
ap.add_argument("--runs", type=int, default=5)
ap.add_argument("--timeout", type=float, default=180)
ap.add_argument("--csv", default="measurements/spawn_times.csv")
ap.add_argument("--keep", action="store_true", help="keep servers running after the final run")
args = ap.parse_args()
if args.users < 1:
    ap.error("--users must be at least 1")
if args.runs < 1:
    ap.error("--runs must be at least 1")
if args.timeout <= 0:
    ap.error("--timeout must be positive")
TOKEN = os.environ.get("JUPYTERHUB_TOKEN")
if not TOKEN:
    ap.error("set the JUPYTERHUB_TOKEN environment variable")
API = args.hub.rstrip("/") + "/hub/api"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Authorization": f"token {TOKEN}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def ensure_user(name):
    st, _ = call("GET", f"/users/{name}")
    if st == 404:
        st, _ = call("POST", f"/users/{name}")
        if st != 201:
            raise RuntimeError(f"failed to create user {name}: HTTP {st}")
    elif st != 200:
        raise RuntimeError(f"failed to read user {name}: HTTP {st}")


def server_ready(name):
    _, u = call("GET", f"/users/{name}")
    s = (u or {}).get("servers", {}).get("", {})
    return bool(s.get("ready"))


def spawn(name):
    t0 = time.perf_counter()
    st, _ = call("POST", f"/users/{name}/server")
    if st not in (201, 202):
        return name, None, f"HTTP {st}"
    while time.perf_counter() - t0 < args.timeout:
        if server_ready(name):
            return name, time.perf_counter() - t0, "ok"
        time.sleep(0.25)
    return name, None, "timeout"


def stop(name):
    call("DELETE", f"/users/{name}/server")
    t0 = time.time()
    while time.time() - t0 < 60:
        _, u = call("GET", f"/users/{name}")
        if not (u or {}).get("servers"):
            return
        time.sleep(0.5)


names = [f"bench{i:02d}" for i in range(1, args.users + 1)]
for n in names:
    ensure_user(n)
    stop(n)

rows = []
for run in range(1, args.runs + 1):
    with ThreadPoolExecutor(max_workers=len(names)) as ex:
        res = list(ex.map(spawn, names))
    for n, t, status in res:
        rows.append({"run": run, "concurrent_users": args.users, "user": n,
                     "startup_seconds": round(t, 2) if t else "", "status": status})
        print(f"run {run} {n}: {status} {t and f'{t:.2f} s' or ''}")
    if run < args.runs or not args.keep:
        for n in names:
            stop(n)
        time.sleep(3)

os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
new = not os.path.exists(args.csv)
with open(args.csv, "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    if new:
        w.writeheader()
    w.writerows(rows)

ok = [r["startup_seconds"] for r in rows if r["status"] == "ok"]
if ok:
    print(f"\nConcurrent users: {args.users} | samples: {len(ok)}/{len(rows)}")
    print(f"mean {statistics.mean(ok):.2f} s | median {statistics.median(ok):.2f} s | "
          f"min {min(ok):.2f} s | max {max(ok):.2f} s"
          + (f" | std.dev. {statistics.stdev(ok):.2f} s" if len(ok) > 1 else ""))
