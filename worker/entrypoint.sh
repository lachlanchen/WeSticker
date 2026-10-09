#!/usr/bin/env bash
set -euo pipefail
test -r /run/secrets/vnc_password || { echo 'A private VNC password file is required.' >&2; exit 1; }
x11vnc -storepasswd "$(cat /run/secrets/vnc_password)" /tmp/vnc-password >/dev/null
Xvfb :88 -screen 0 1440x1000x24 -nolisten tcp &
sleep 1
openbox >/tmp/openbox.log 2>&1 &
chromium --no-sandbox --disable-dev-shm-usage --no-first-run --user-data-dir=/profile --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --start-maximized https://sticker.weixin.qq.com/ >/tmp/chromium.log 2>&1 &
x11vnc -display :88 -localhost -rfbport 5900 -rfbauth /tmp/vnc-password -forever -shared >/tmp/vnc.log 2>&1 &
exec websockify --web=/usr/share/novnc 6080 127.0.0.1:5900
