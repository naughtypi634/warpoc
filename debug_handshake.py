"""Temporary diagnostic: test WARP WireGuard handshake from this machine."""
import base64
import configparser
import hashlib
import os
import socket
import struct
import time

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

WARP_PUB = base64.b64decode("bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=")


def H(x):
    return hashlib.blake2s(x, digest_size=32).digest()


def mac16(key, x):
    return hashlib.blake2s(x, key=key, digest_size=16).digest()


def kdf2(ck, data):
    t0 = hashlib.blake2s(data, key=ck, digest_size=32).digest()
    return t0, hashlib.blake2s(b"\x01", key=t0, digest_size=32).digest()


def handshake(priv_b64, endpoint, timeout=6):
    init_static = base64.b64decode(priv_b64)
    init_pub = X25519PrivateKey.from_private_bytes(init_static).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    eph = X25519PrivateKey.generate()
    eph_pub = eph.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    eph_priv = eph.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )

    ck = H(b"Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s")
    ck, k = kdf2(ck, X25519PrivateKey.from_private_bytes(eph_priv).exchange(
        X25519PublicKey.from_public_bytes(WARP_PUB)))
    enc_static = ChaCha20Poly1305(k).encrypt(b"\x00" * 12, init_pub, b"")
    ck, k = kdf2(ck, X25519PrivateKey.from_private_bytes(init_static).exchange(
        X25519PublicKey.from_public_bytes(WARP_PUB)))
    enc_ts = ChaCha20Poly1305(k).encrypt(
        b"\x00" * 12, struct.pack("<Q", int(time.time())) + b"\x00" * 4, H(init_pub))

    msg = b"\x01\x00\x00\x00" + os.urandom(4) + eph_pub + enc_static + enc_ts
    mac1_key = H(b"mac1----" + WARP_PUB)
    msg += mac16(mac1_key, msg)
    msg += mac16(H(b"mac2----" + init_pub), msg)
    assert len(msg) == 148

    host, port = endpoint.rsplit(":", 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    s.sendto(msg, (host, int(port)))
    try:
        data, _ = s.recvfrom(2048)
    except socket.timeout:
        return "TIMEOUT"
    if len(data) < 92:
        return f"SHORT({len(data)}) first={data[:5].hex()}"
    if data[0] != 2:
        return f"TYPE={data[0]} first={data[:5].hex()}"
    ok = data[76:92] == mac16(mac1_key, data[:76])
    return f"RESPONSE mac1_ok={ok} len={len(data)}"


if __name__ == "__main__":
    # Control: UDP DNS query to prove UDP egress works from this machine
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(6)
        # minimal DNS query for "example.com" A record to 1.1.1.1:53
        txid = b"\x12\x34"
        dns = txid + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        dns += b"\x07example\x03com\x00\x00\x01\x00\x01"
        s.sendto(dns, ("1.1.1.1", 53))
        data, _ = s.recvfrom(2048)
        print(f"UDP DNS 1.1.1.1:53 -> OK {len(data)} bytes", flush=True)
    except Exception as e:
        print(f"UDP DNS 1.1.1.1:53 -> FAIL {e}", flush=True)

    cfg = configparser.ConfigParser()
    cfg.read("wgcf-profile.conf")
    priv = cfg["Interface"]["PrivateKey"].strip()
    endpoints = [
        "engage.cloudflareclient.com:2408",
        "162.159.192.6:2408",
        "162.159.193.218:1387",
        "188.114.97.63:3476",
        "1.1.1.1:2408",
    ]
    for ep in endpoints:
        print(f"{ep} -> {handshake(priv, ep)}", flush=True)
