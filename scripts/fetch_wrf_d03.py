#!/usr/bin/env python3
"""Scarica dal server OPeNDAP di meteo@uniparthenope un sottoinsieme delle uscite orarie
del modello WRF (dominio d03, Campania, ~3 km) e lo salva nell'area raw della piattaforma.

Per ogni ora vengono trasferite solo le variabili superficiali necessarie al caso d'uso
(OPeNDAP invia solo i dati richiesti, non l'intero file da ~140 MB).

Uso sull'host (con l'immagine utente, che contiene xarray e netCDF4):
  sudo docker run --rm --entrypoint python -u 1000 \
      -v /opt/weather/data/raw/models:/out -v ~/wxhub/scripts:/scripts:ro \
      wxhub-singleuser:latest /scripts/fetch_wrf_d03.py --start 2026-11-13 --days 5 --out /out/wrf5_d03
"""
import argparse
import csv
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import xarray as xr

BASE = "https://data.meteo.uniparthenope.it/opendap/hyrax/wrf5/d03/history"
VARS = ["T2", "U10", "V10", "RAINC", "RAINNC", "PSFC"]
STATIC = ["XLAT", "XLONG", "LANDMASK", "HGT"]

ap = argparse.ArgumentParser()
ap.add_argument("--start", required=True, help="primo giorno, AAAA-MM-GG")
ap.add_argument("--days", type=int, default=5)
ap.add_argument("--out", default="/out/wrf5_d03")
ap.add_argument("--base", default=BASE)
ap.add_argument("--retries", type=int, default=3)
args = ap.parse_args()
if args.days < 1:
    ap.error("--days deve essere almeno 1")
if args.retries < 1:
    ap.error("--retries deve essere almeno 1")

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
t0 = datetime.strptime(args.start, "%Y-%m-%d")
hours = [t0 + timedelta(hours=h) for h in range(24 * args.days)]


def url_for(t):
    return f"{args.base}/{t:%Y/%m/%d}/wrf5_d03_{t:%Y%m%d}Z{t:%H}00.nc"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


log = []
grid_done = (out / "wrf5_d03_grid.nc").exists()
t_start = time.perf_counter()
for i, t in enumerate(hours, 1):
    dest = out / f"wrf5_d03_{t:%Y%m%d}Z{t:%H}00.nc"
    if dest.exists():
        log.append({"ora": f"{t:%Y-%m-%d %H}:00", "file": dest.name, "esito": "gia presente",
                    "sha256": sha256(dest)})
        continue
    esito = "mancante"
    for k in range(args.retries):
        src = None
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            src = xr.open_dataset(url_for(t), engine="netcdf4", decode_times=False, decode_coords=False)
            if not grid_done:
                g = src[STATIC].isel(Time=0).load()
                g.attrs = {"source": "meteo@uniparthenope WRF5 d03", "url": url_for(t)}
                g.to_netcdf(out / "wrf5_d03_grid.nc")
                grid_done = True
            sub = src[VARS].isel(Time=0).load()
            sub = sub.expand_dims(time=[np.datetime64(t, "ns")])
            sub.attrs = {"source": "meteo@uniparthenope WRF5 d03 (history)", "url": url_for(t)}
            enc = {v: {"zlib": True, "complevel": 4} for v in VARS}
            sub.to_netcdf(tmp, encoding=enc)
            tmp.replace(dest)
            esito = "ok"
            break
        except Exception as e:  # file assente sul server o errore di rete
            esito = f"errore: {type(e).__name__}"
            tmp.unlink(missing_ok=True)
            time.sleep(2 * (k + 1))
        finally:
            if src is not None:
                src.close()
    log.append({"ora": f"{t:%Y-%m-%d %H}:00", "file": dest.name if esito == "ok" else "",
                "esito": esito, "sha256": sha256(dest) if esito == "ok" else ""})
    print(f"[{i:3d}/{len(hours)}] {t:%Y-%m-%d %H}:00  {esito}", flush=True)

with open(out / "manifest.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["ora", "file", "esito", "sha256"])
    w.writeheader()
    w.writerows(log)
ok = sum(r["esito"] in ("ok", "gia presente") for r in log)
mb = sum(p.stat().st_size for p in out.glob("wrf5_d03_*.nc")) / 1e6
print(f"\nOre disponibili: {ok}/{len(hours)} | {mb:.0f} MB in {out} | "
      f"{time.perf_counter() - t_start:.0f} s | elenco in manifest.csv")
