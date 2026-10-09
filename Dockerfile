FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY src ./src
COPY public ./public
COPY scripts/asset_manifest.mjs ./scripts/asset_manifest.mjs
COPY index.html tsconfig.json vite.config.ts ./
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server ./server
COPY scripts/retention.py ./scripts/retention.py
COPY --from=frontend /app/dist ./dist
COPY public/catalog.json ./public/catalog.json
RUN useradd --uid 10001 --create-home westicker && mkdir /data && chown westicker /data
USER westicker
ENV WESTICKER_CONFIG=/run/secrets/westicker.json
EXPOSE 8000
CMD ["gunicorn","--preload","--workers","2","--threads","4","--timeout","60","--bind","0.0.0.0:8000","server.app:create_app()"]
