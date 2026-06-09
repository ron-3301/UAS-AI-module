# tests for the udp emitter (loopback) and the in-memory + chained variants.
from __future__ import annotations

import json
import socket

from src.output.udp_emitter import InMemoryEmitter, UdpEmitter, chained


def test_inmemory_emitter_buffers_packets() -> None:
    em = InMemoryEmitter()
    em({"a": 1})
    em({"b": 2})
    assert em.packets == [{"a": 1}, {"b": 2}]


def test_chained_emitter_fans_out() -> None:
    a = InMemoryEmitter()
    b = InMemoryEmitter()
    em = chained(a, b)
    em({"frame": 7})
    assert a.packets == b.packets == [{"frame": 7}]


def test_udp_emitter_loopback() -> None:
    # Bind a receiver on an ephemeral loopback port.
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    port = rx.getsockname()[1]
    rx.settimeout(2.0)

    em = UdpEmitter(addr="127.0.0.1", port=port, broadcast=False)
    em({"hello": "world", "n": 42})
    data, _addr = rx.recvfrom(2048)
    em.close()
    rx.close()

    assert json.loads(data.decode("utf-8")) == {"hello": "world", "n": 42}
