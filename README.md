# wxhub – ambiente interattivo JupyterHub per dati meteo-marini

Repository della tesi di laurea triennale in Informatica (Università degli Studi di Napoli
"Parthenope") *Sviluppo e messa in produzione di un ambiente interattivo basato su Jupyter
Notebook* – Mariano Pio Stora, relatore Prof. Raffaele Montella.

La piattaforma fornisce a ogni utente autenticato un server JupyterLab isolato in un container
Docker, con lo stack scientifico (Xarray, Dask, Zarr, NetCDF4, cfgrib, Voilà, Papermill) e
l'accesso in sola lettura ai dati locali.

## Struttura

| Percorso | Contenuto |
|---|---|
| `docker-compose.yml` | servizio JupyterHub, rete `wxhub-net`, volume dello stato |
| `jupyterhub/` | Dockerfile dell'Hub (JupyterHub 5.3.0) e `jupyterhub_config.py` |
| `image/` | Dockerfile (base `scipy-notebook:2025-12-31`) e dipendenze dell'immagine utente |
| `templates/` | notebook template condivisi (montati in sola lettura) |
| `notebooks/` | caso d'uso WRF Campania (dati meteo@uniparthenope) e dashboard Voilà |
| `scripts/` | download dati WRF via OPeNDAP, test dei permessi, misure, Papermill |

## Requisiti

Linux x86_64, Docker Engine con plugin Compose v2, 4 GB di RAM liberi, porta 8000.

## Installazione

I percorsi dell'host usati dalla configurazione sono `/opt/weather/data/{raw/sensors,raw/models,curated}`
per i dati e `~/wxhub/templates` per i template (vedi `c.DockerSpawner.volumes` in
`jupyterhub/jupyterhub_config.py`: le chiavi sono percorsi dell'HOST). Se il repository non è clonato in
`/home/aulainfo/wxhub`, aggiornare il percorso dei template in quel file.

```bash
git clone https://github.com/<utente>/wxhub.git ~/wxhub && cd ~/wxhub
sudo mkdir -p /opt/weather/data/raw/sensors /opt/weather/data/raw/models /opt/weather/data/curated
sudo chown -R $USER /opt/weather/data
docker build -t wxhub-singleuser:latest ./image
docker compose up -d --build
docker compose logs -f jupyterhub               # attendere "JupyterHub is now running"
```

Aprire `http://<host>:8000`, registrare `admin` con *Sign up*. Possono accedere solo gli utenti
elencati in `c.Authenticator.allowed_users`.

## Caso d'uso

Evento di maltempo del 13-17 novembre 2026 in Campania, analizzato con le uscite orarie del modello WRF
del Centro meteo@uniparthenope (dominio d03, ~3 km, dati aperti IODL 2.0, server OPeNDAP
`https://data.meteo.uniparthenope.it/opendap/`).

1. Scaricare le variabili superficiali nell'area raw (sull'host):
   ```bash
   sudo docker run --rm --entrypoint python -u 1000 \
     -v /opt/weather/data/raw/models:/out -v ~/wxhub/scripts:/scripts:ro \
     wxhub-singleuser:latest /scripts/fetch_wrf_d03.py --start 2026-11-13 --days 5 --out /out/wrf5_d03
   ```
2. In JupyterLab copiare `notebooks/` in `~/work/notebooks` ed eseguire `caso_uso_wrf_campania.ipynb`,
   oppure `./scripts/run_papermill.sh 2026-11-15T00 2026-11-15T23 Salerno`.
3. Dashboard: `http://<host>:8000/user/<utente>/voila/render/notebooks/dashboard_wrf_voila.ipynb`.

## Verifiche e misure

```bash
./scripts/test_permissions.sh                     # nel terminale JupyterLab
export JUPYTERHUB_TOKEN=<token admin da /hub/token>
python3 scripts/measure_spawn.py --users 1 --runs 5
python3 scripts/measure_spawn.py --users 5 --runs 3 --keep
./scripts/measure_load.sh 5
```

## Riproducibilità

Le immagini base sono fissate (`scipy-notebook:2025-12-31`, `jupyterhub:5.3.0`). Dopo la build eseguire
`./scripts/freeze_env.sh`: registra in `image/requirements.lock` le versioni esatte delle librerie e in
`image/IMAGE_ID` l'identificativo dell'immagine; committare entrambi i file.

## Limiti noti

Prototipo su singolo host: HTTP senza TLS, registrazione aperta (limitata da `allowed_users`),
socket Docker montato nell'Hub, nessuno spegnimento dei server inattivi. Vedere il capitolo sulla sicurezza della tesi prima di esporlo in rete.

## Licenza

Codice: MIT. Dati WRF: meteo@uniparthenope, Italian Open Data License v2.0.
