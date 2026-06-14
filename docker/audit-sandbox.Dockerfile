FROM python:3.12-slim-bookworm@sha256:76d4b7b6305788c6b4c6a19d6a22a3921bf802e9af4d5e1e5bd771208dba74bf

RUN apt-get -o Acquire::Retries=5 update \
    && apt-get install -y --no-install-recommends \
        bash \
        coreutils \
        findutils \
        iproute2 \
        procps \
        strace

RUN useradd --create-home --home-dir /home/audit --shell /bin/sh audit

USER audit
WORKDIR /workspace
