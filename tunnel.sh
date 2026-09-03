#!/usr/bin/env bash
# ==============================================================================
# SSB Document Screening System — Live Public Internet Tunnel (Free Cloudflare)
# ==============================================================================

echo "==================================================="
echo "  Launching Free Live Public HTTPS Tunnel"
echo "==================================================="

# Ensure dev server is running
if ! curl -s http://localhost:5173 > /dev/null; then
    echo "Starting local dev workstation first..."
    ./start-dev.sh
    sleep 3
fi

echo "Connecting to Cloudflare Global Edge Network..."
cloudflared tunnel --url http://localhost:5173
