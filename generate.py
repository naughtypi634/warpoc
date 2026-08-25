#!/usr/bin/env python3
"""Free Cloudflare WARP -> OpenClash / Mihomo subscription generator.

Registers fresh WARP accounts through Cloudflare's mobile API (free, the
account is reported as warp_plus=true), builds WireGuard proxies over a set
of optimized WARP anycast endpoints, merges any user-provided wgcf-format
profiles from ./profiles, and writes a complete Clash YAML to output/warp.yaml.

Environment:
    ACCOUNT_COUNT   number of fresh WARP accounts to register (default 3)
"""
from __future__ import annotations

import base64
import configparser
import glob
import os
import random
import string
import sys
import time
from pathlib import Path

import requests
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

API_URL = "https://api.cloudflareclient.com/v0i2310010000"
HEADERS = {
    "User-Agent": "1.1.1.1/6.23",
    "CF-Client-Version": "i-6.23-2308311933.1",
    "Content-Type": "application/json; charset=UTF-8",
    "Host": "api.cloudflareclient.com",
    "Connection": "Keep-Alive",
}

# WARP anycast endpoints (IP:port), verified by a real WireGuard handshake
# scan from the user's network on 2026-08-25 (0% loss, 209-218 ms).
# Replace/extend with your own 优选 IP list if your network changes.
ENDPOINTS = [
    "engage.cloudflareclient.com:2408",
    "162.159.193.218:1387",
    "162.159.195.165:1387",
    "162.159.192.142:1387",
    "162.159.193.18:1387",
    "162.159.193.236:1387",
    "162.159.193.63:3476",
    "188.114.97.63:3476",
    "162.159.192.109:3476",
    "162.159.193.3:1387",
    "162.159.193.99:1387",
    "188.114.97.76:3476",
    "162.159.193.172:3476",
    "162.159.193.216:1387",
    "162.159.192.86:3476",
    "162.159.193.6:1387",
    "162.159.195.131:1387",
    "188.114.97.218:1387",
    "162.159.192.167:3476",
    "162.159.193.125:3476",
    "162.159.193.179:1387",
    "162.159.193.28:1387",
    "162.159.195.237:3476",
    "188.114.97.86:3476",
    "162.159.192.20:3476",
]

MTU = 1280
ACCOUNT_COUNT = int(os.environ.get("ACCOUNT_COUNT", "3"))
OUT = Path("output/warp.yaml")


def rand_str(n: int) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def make_keypair() -> tuple[str, str]:
    """Return (private_key_b64, public_key_b64) for WireGuard."""
    priv = X25519PrivateKey.generate()
    pub_b64 = base64.b64encode(
        priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
    ).decode()
    priv_b64 = base64.b64encode(
        priv.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
    ).decode()
    return priv_b64, pub_b64


def register_account() -> tuple[dict, str]:
    """Register a fresh free WARP account, return (result, private_key_b64)."""
    priv_b64, pub_b64 = make_keypair()
    install_id = rand_str(43)
    payload = {
        "fcm_token": f"{install_id}:APA91b{rand_str(134)}",
        "install_id": install_id,
        "key": pub_b64,
        "warp_enabled": True,
        "locale": random.choice(["en_US", "zh_CN", "ja_JP"]),
        "model": random.choice(["iPhone16,2", "iPhone15,3", "iPad13,4"]),
        "tos": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "type": "IOS",
    }
    resp = requests.post(f"{API_URL}/reg", json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["result"], priv_b64


def reserved_from_client_id(client_id: str) -> list[int]:
    """Decode WARP client_id (base64, 3 bytes) into Clash `reserved`."""
    try:
        raw = base64.b64decode(client_id + "=" * (-len(client_id) % 4))
        return list(raw[:3])
    except Exception:
        return [0, 0, 0]


def wireguard_proxy(name: str, server: str, port: int, account: dict, priv_b64: str) -> dict:
    cfg = account["config"]
    return {
        "name": name,
        "type": "wireguard",
        "server": server,
        "port": port,
        "ip": cfg["interface"]["addresses"]["v4"],
        "private-key": priv_b64,
        "public-key": cfg["peers"][0]["public_key"],
        "reserved": reserved_from_client_id(cfg.get("client_id", "")),
        "udp": True,
        "mtu": MTU,
        "allowed-ips": ["0.0.0.0/0"],
    }


def profile_proxy(path: str) -> dict | None:
    """Parse a wgcf-format profile (*.conf) into a Clash wireguard proxy."""
    cfg = configparser.ConfigParser()
    cfg.read(path)
    if "Interface" not in cfg or "Peer" not in cfg:
        return None
    interface = cfg["Interface"]
    peer = cfg["Peer"]
    endpoint = peer.get("Endpoint", "").strip()
    if not endpoint or ":" not in endpoint:
        return None
    server, port = endpoint.rsplit(":", 1)
    proxy = {
        "name": Path(path).stem.replace("_", "-"),
        "type": "wireguard",
        "server": server,
        "port": int(port),
        "ip": interface["Address"].split(",")[0].strip().split("/")[0],
        "private-key": interface["PrivateKey"].strip(),
        "public-key": peer["PublicKey"].strip(),
        "allowed-ips": ["0.0.0.0/0"],
        "udp": True,
        "mtu": int(interface.get("MTU", "1280")),
    }
    reserved = peer.get("Reserved", "").strip()
    if reserved:
        try:
            proxy["reserved"] = [int(x.strip()) for x in reserved.split(",")]
        except ValueError:
            pass
    return proxy


def build_config(proxies: list[dict]) -> dict:
    names = [p["name"] for p in proxies]
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
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "WARP-AUTO",
                "type": "url-test",
                "url": "https://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": names,
            },
            {
                "name": "WARP",
                "type": "select",
                "proxies": ["WARP-AUTO"] + names,
            },
        ],
        "rules": ["GEOIP,CN,DIRECT", "MATCH,WARP"],
    }


def main() -> None:
    proxies: list[dict] = []

    for i in range(1, ACCOUNT_COUNT + 1):
        try:
            account, priv_b64 = register_account()
        except requests.RequestException as exc:
            print(f"account {i} registration failed: {exc}", file=sys.stderr)
            time.sleep(2)
            continue
        for j, ep in enumerate(ENDPOINTS, 1):
            server, port = ep.rsplit(":", 1)
            proxies.append(
                wireguard_proxy(
                    f"WARP-{i:02d}-{j:02d}", server, int(port), account, priv_b64
                )
            )
        print(f"registered account {i}/{ACCOUNT_COUNT}")
        time.sleep(1)

    for fn in sorted(glob.glob("profiles/*.conf")):
        proxy = profile_proxy(fn)
        if proxy:
            proxies.append(proxy)
            print(f"merged profile {fn}")

    if not proxies:
        raise SystemExit("No WARP proxies generated.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(build_config(proxies), f, allow_unicode=True, sort_keys=False)
    print(f"Generated {len(proxies)} proxies -> {OUT}")


if __name__ == "__main__":
    main()
