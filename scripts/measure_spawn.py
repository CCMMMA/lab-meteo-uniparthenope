#!/usr/bin/env python3
"""Misura il tempo di avvio dei server JupyterLab tramite la REST API di JupyterHub.

Uso (sull'host, con un token generato dall'amministratore nella pagina /hub/token):
    export JUPYTERHUB_TOKEN=...            # token dell'utente admin
    python3 scripts/measure_spawn.py --users 1 --runs 5      # avvio singolo, 5 ripetizioni
    python3 scripts/measure_spawn.py --users 5 --runs 3      # 5 utenti contemporanei

Per ogni ripetizione: crea (se mancano) gli utenti bench01..benchNN, avvia in parallelo
i loro server, misura il tempo fino a "ready", poi li arresta. Output: CSV + riepilogo.
Richiede solo la libreria standard di Python.
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
ap.add_argument("--csv", default="misure/spawn_times.csv")
ap.add_argument("--keep", action="store_true", help="lascia attivi i server dopo l'ultima ripetizione")
args = ap.parse_args()
TOKEN = os.environ["JUPYTERHUB_TOKEN"]
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
        call("POST", f"/users/{name}")


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
    for n, t, esito in res:
        rows.append({"run": run, "utenti_concorrenti": args.users, "utente": n,
                     "tempo_avvio_s": round(t, 2) if t else "", "esito": esito})
        print(f"run {run} {n}: {esito} {t and f'{t:.2f} s' or ''}")
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

ok = [r["tempo_avvio_s"] for r in rows if r["esito"] == "ok"]
if ok:
    print(f"\nUtenti concorrenti: {args.users} | campioni: {len(ok)}/{len(rows)}")
    print(f"media {statistics.mean(ok):.2f} s | mediana {statistics.median(ok):.2f} s | "
          f"min {min(ok):.2f} s | max {max(ok):.2f} s"
          + (f" | dev.std {statistics.stdev(ok):.2f} s" if len(ok) > 1 else ""))
