#!/usr/bin/env bash
set -Eeuo pipefail

: "${DISPLAY:=:1}"
: "${VNC_PORT:=7778}"
: "${NOVNC_PORT:=6080}"
: "${VNC_PASSWORD:=ros}"
: "${VNC_RESOLUTION:=1600x900}"

display_number="${DISPLAY#:}"
vnc_dir="${HOME}/.vnc"

if command -v tigervncpasswd >/dev/null 2>&1; then
  vncpasswd_cmd=tigervncpasswd
elif command -v vncpasswd >/dev/null 2>&1; then
  vncpasswd_cmd=vncpasswd
else
  echo "Error: tigervncpasswd is not installed (package: tigervnc-tools)." >&2
  exit 1
fi

if command -v tigervncserver >/dev/null 2>&1; then
  vncserver_cmd=tigervncserver
elif command -v vncserver >/dev/null 2>&1; then
  vncserver_cmd=vncserver
else
  echo "Error: tigervncserver is not installed." >&2
  exit 1
fi

mkdir -p "${vnc_dir}" "${HOME}/.config/xfce4/xfconf/xfce-perchannel-xml"
chmod 700 "${vnc_dir}"

# This directory is a named volume shared with the compute container.
# X11 local-user authorization below permits the same container user to use it.
sudo mkdir -p /tmp/.X11-unix
sudo chmod 1777 /tmp/.X11-unix

printf '%s\n' "${VNC_PASSWORD}" | "${vncpasswd_cmd}" -f > "${vnc_dir}/passwd"
chmod 600 "${vnc_dir}/passwd"

cat > "${vnc_dir}/xstartup" <<'EOF'
#!/usr/bin/env bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export XDG_SESSION_TYPE=x11
export GDK_BACKEND=x11
xset s off
xset -dpms
xset s noblank
exec dbus-launch --exit-with-session startxfce4
EOF
chmod +x "${vnc_dir}/xstartup"

cat > "${HOME}/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-power-manager.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-power-manager" version="1.0">
  <property name="xfce4-power-manager" type="empty">
    <property name="dpms-enabled" type="bool" value="false"/>
    <property name="blank-on-ac" type="int" value="0"/>
    <property name="blank-on-battery" type="int" value="0"/>
  </property>
</channel>
EOF

"${vncserver_cmd}" -kill ":${display_number}" >/dev/null 2>&1 || true
sudo rm -f "/tmp/.X${display_number}-lock" "/tmp/.X11-unix/X${display_number}"

cleanup() {
  if [[ -n "${websockify_pid:-}" ]]; then
    kill "${websockify_pid}" >/dev/null 2>&1 || true
  fi
  "${vncserver_cmd}" -kill ":${display_number}" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

"${vncserver_cmd}" ":${display_number}" \
  -rfbport "${VNC_PORT}" \
  -geometry "${VNC_RESOLUTION}" \
  -depth 24 \
  -localhost no

# Allow the same UID in the compute container to connect through the shared
# Unix-domain socket without sharing the VNC container's Xauthority cookie.
DISPLAY="${DISPLAY}" xhost "+SI:localuser:$(id -un)"

novnc_web_root=/usr/share/novnc
if [[ ! -f "${novnc_web_root}/vnc.html" ]]; then
  echo "Error: noVNC web client not found at ${novnc_web_root}/vnc.html." >&2
  exit 1
fi

websockify --web "${novnc_web_root}" \
  "0.0.0.0:${NOVNC_PORT}" "127.0.0.1:${VNC_PORT}" &
websockify_pid=$!

echo "TurtleBot VNC is ready on port ${VNC_PORT} (DISPLAY=${DISPLAY})"
echo "TurtleBot noVNC is ready at http://localhost:${NOVNC_PORT}/vnc.html"
echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-77}"

tail -F "${vnc_dir}"/*.log &
tail_pid=$!
wait -n "${websockify_pid}" "${tail_pid}"
