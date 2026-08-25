#!/usr/bin/env python3
"""Generate a VLESS OpenClash / Mihomo subscription mirror from repo secrets.

Primary subscription comes from the deployed edgetunnel worker itself
(https://<your-domain>/<KEY>). This script is a fallback mirror that builds a
static Clash YAML from the same VLESS node and publishes it to output/vless.yaml.

Environment (set as GitHub Actions secrets):
    VLESS_UUID   UUID of the deployed edgetunnel node (UUIDv4)
    VLESS_HOST   hostname/domain of the deployed worker
    VLESS_PORT   optional, default 443
    VLESS_PATH   optional, default "/?ed=2048"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

UUID = os.environ.get("VLESS_UUID", "").strip()
HOST = os.environ.get("VLESS_HOST", "").strip()
PORT = int(os.environ.get("VLESS_PORT", "443"))
PATH = os.environ.get("VLESS_PATH", "/?ed=2048")
OUT = Path("output/vless.yaml")


def build_config(uuid: str, host: str, port: int, path: str) -> dict:
    proxy = {
        "name": "CF-Worker",
        "type": "vless",
        "server": host,
        "port": port,
        "uuid": uuid,
        "network": "ws",
        "tls": True,
        "servername": host,
        "ws-opts": {
            "path": path,
            "headers": {"Host": host},
        },
    }
    return {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "dns": {
            "enable": True,
            "enhanced-mode": "fake-ip",
            "fake-ip-range": "198.18.0.1/16",
            "nameserver": ["223.5.5.5", "119.29.29.29"],
            "fallback": ["1.1.1.1", "8.8.8.8"],
        },
        "proxies": [proxy],
        "proxy-groups": [
            {
                "name": "CF-AUTO",
                "type": "url-test",
                "url": "https://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": ["CF-Worker"],
            },
            {
                "name": "CF",
                "type": "select",
                "proxies": ["CF-AUTO", "CF-Worker"],
            },
        ],
        "rules": ["GEOIP,CN,DIRECT", "MATCH,CF"],
    }


def main() -> None:
    if not UUID or not HOST:
        print("VLESS_UUID / VLESS_HOST not configured; skipping generation.", file=sys.stderr)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(build_config(UUID, HOST, PORT, PATH), f, allow_unicode=True, sort_keys=False)
    print(f"Generated VLESS subscription -> {OUT}")


if __name__ == "__main__":
    main()
