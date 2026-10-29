FROM node:22-bookworm-slim AS codex
RUN npm install --global --omit=dev @openai/codex@0.165.0

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CODEX_HOME=/codex HOME=/home/broker BROKER_OUTPUT_DIR=/outputs
RUN apt-get update && apt-get install --yes --no-install-recommends ca-certificates libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 1000 --create-home broker \
    && mkdir /codex /outputs && chown broker:broker /codex /outputs
COPY --from=codex /usr/local/bin/node /usr/local/bin/node
COPY --from=codex /usr/local/lib/node_modules/@openai /usr/local/lib/node_modules/@openai
RUN ln -s /usr/local/lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex \
    && codex --version
WORKDIR /app
COPY broker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY broker ./broker
USER broker
EXPOSE 8030
HEALTHCHECK --interval=10s --timeout=4s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8030/health',timeout=3)"
CMD ["uvicorn","broker.app:app","--host","0.0.0.0","--port","8030","--no-access-log"]
