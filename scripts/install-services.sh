#!/bin/bash
# Install qtadmin systemd services
# Run as root: sudo bash scripts/install-services.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MANIFESTS_DIR="$SCRIPT_DIR/../manifests"

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: must run as root (sudo)"
    exit 1
fi

SERVICES=(
    "qtadmin-provider.service"
    "qtadmin-mail-sender.service"
)

for svc in "${SERVICES[@]}"; do
    src="$MANIFESTS_DIR/$svc"
    if [ ! -f "$src" ]; then
        echo "WARNING: $src not found, skipping"
        continue
    fi
    cp "$src" "/etc/systemd/system/$svc"
    echo "Installed $svc"
done

systemctl daemon-reload

for svc in "${SERVICES[@]}"; do
    systemctl enable "$svc"
    systemctl restart "$svc" || echo "WARNING: $svc failed to start (may need user/config setup)"
done

echo ""
echo "=== Status ==="
for svc in "${SERVICES[@]}"; do
    systemctl status "$svc" --no-pager 2>&1 | head -5
    echo ""
done

echo ""
echo "Commands:"
echo "  systemctl status qtadmin-provider       # check provider status"
echo "  journalctl -u qtadmin-provider -f       # tail provider logs"
echo "  systemctl status qtadmin-mail-sender     # check mail sender status"
echo "  journalctl -u qtadmin-mail-sender -f    # tail mail sender logs"
