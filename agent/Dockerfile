FROM node:22-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392
WORKDIR /opt/aginti
COPY --from=aginti package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund
COPY --from=aginti src ./src
COPY --from=aginti LICENSE ./LICENSE
WORKDIR /app
COPY --chown=node:node agent/*.mjs ./agent/
RUN mkdir /data && chown node:node /data
USER node
ENV NODE_ENV=production
EXPOSE 8001
CMD ["node", "agent/server.mjs"]
