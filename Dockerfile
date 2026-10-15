FROM node:22-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392 AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY src ./src
COPY public ./public
COPY scripts/asset_manifest.mjs ./scripts/asset_manifest.mjs
COPY index.html tsconfig.json vite.config.ts ./
RUN npm run build

FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk fonts-dejavu-core ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=1000:1000 server ./server
COPY --chown=1000:1000 scripts/retention.py ./scripts/retention.py
COPY --chown=1000:1000 --from=frontend /app/dist ./dist
COPY --chown=1000:1000 public/catalog.json ./public/catalog.json
RUN useradd --uid 1000 --create-home westicker && mkdir /data && chown westicker /data
USER westicker
ENV WESTICKER_CONFIG=/run/secrets/westicker.json PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["gunicorn","--workers","1","--threads","4","--timeout","120","--bind","0.0.0.0:8000","server.app:create_app()"]
