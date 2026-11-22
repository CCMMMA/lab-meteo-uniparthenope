FROM quay.io/jupyter/scipy-notebook:2025-12-31@sha256:aebf73afaf983124e075904ec7856c4b511d0415d1275835a6f08704422ece9e

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gfortran \
        libproj-dev \
        proj-data \
        proj-bin  \
        libgeos-dev  \
        libeccodes-dev  \
        gcc  \
        g++  \
        git  \
        curl &&  \
    apt-get clean &&  \
    rm -rf /var/lib/apt/lists/*

USER ${NB_UID}

COPY requirements.txt /tmp/requirements.txt
RUN  pip install --no-cache-dir -r /tmp/requirements.txt && \
     python -m jupyter server extension enable voila.server_extension --sys-prefix

RUN mkdir -p /home/jovyan/templates \
             /home/jovyan/shared \
             /home/jovyan/work


