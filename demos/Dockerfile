FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS builder

RUN python -m pip install --no-cache-dir \
    jupyterlite-core==0.8.7 \
    jupyterlite-pyodide-kernel==0.8.7 \
    jupyterlab-widgets==3.0.17 \
    jupyter-server==2.17.0

WORKDIR /lite
COPY demos/*.ipynb /lite/files/
COPY demos/jupyter-lite.json demos/overrides.json demos/build_gallery.py /lite/
RUN jupyter lite build --output-dir /site --base-url /services/demos/ && \
    jupyter lite check --output-dir /site && \
    python /lite/build_gallery.py /lite/files /site/gallery.html

FROM nginx:1.29.6-alpine@sha256:f46cb72c7df02710e693e863a983ac42f6a9579058a59a35f1ae36c9958e4ce0
COPY demos/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /site /usr/share/nginx/html
COPY demos/lab.css /usr/share/nginx/html/lab-meteo-v6.css
COPY jupyterhub/assets/logo.png /usr/share/nginx/html/lab-meteo-logo.png
