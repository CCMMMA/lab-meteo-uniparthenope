FROM quay.io/jupyterhub/jupyterhub:5.3.0@sha256:bc6fe7c7f2c9be15dab47cefc49b4ce42b17f2a1f7132b9a61c44feadf754ad9

RUN python3 -m pip install --no-cache-dir \
    dockerspawner==14.0.0 \
    jupyterhub-nativeauthenticator==1.4.0 \
    oauthenticator==17.3.0 \
    jupyterhub-idle-culler==1.4.0

COPY wxhub_ext /srv/jupyterhub/wxhub_ext
COPY assets /srv/jupyterhub/assets
