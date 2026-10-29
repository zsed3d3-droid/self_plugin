FROM node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da
WORKDIR /app
COPY . .
RUN if [ -f package-lock.json ]; then npm ci --ignore-scripts --no-audit --no-fund; else npm install --ignore-scripts --no-audit --no-fund; fi
RUN npm run build
RUN mkdir -p /data/frames && chown -R node:node /data
USER node
EXPOSE 8862
CMD ["node","server.mjs"]
