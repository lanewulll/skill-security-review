FROM python:3.12-slim-bookworm

RUN apt-get -o Acquire::Retries=5 update \
    && apt-get install -y --no-install-recommends \
        bash \
        coreutils \
        findutils \
        iproute2 \
        procps \
        strace \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --home-dir /home/audit --shell /bin/sh audit

USER audit
WORKDIR /workspace
