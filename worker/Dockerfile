FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends chromium xvfb x11vnc novnc websockify openbox tini fonts-noto-cjk ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /agent
RUN npm install --omit=dev playwright-core@1.61.1
COPY wechat-agent.mjs entrypoint.sh ./
RUN chmod +x entrypoint.sh && useradd --create-home --uid 10001 browser && mkdir /profile /work && chown browser:browser /profile /work
USER browser
ENV DISPLAY=:88
ENTRYPOINT ["/usr/bin/tini","--","/agent/entrypoint.sh"]
