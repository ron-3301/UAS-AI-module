# layer 5 - UDP emitter for the targeting packet.
# thin wrapper over stdlib socket. defaults to broadcast (docs/08 §2).
# InMemoryEmitter exists so pytest can grab packets w/o opening a socket.
from __future__ import annotations

import json
import socket
from collections.abc import Callable
from typing import Any


class UdpEmitter:
    def __init__(self, addr: str = "192.168.1.255", port: int = 5005,
                 broadcast: bool = True) -> None:
        self.addr = addr
        self.port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if broadcast:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def __call__(self, pkt: dict[str, Any]) -> None:
        buf = json.dumps(pkt, separators=(",", ":")).encode("utf-8")
        self._sock.sendto(buf, (self.addr, self.port))

    def close(self) -> None:
        self._sock.close()


class InMemoryEmitter:
    # buffers packets in a list. for tests + replay.
    def __init__(self) -> None:
        self.packets: list[dict[str, Any]] = []

    def __call__(self, pkt: dict[str, Any]) -> None:
        self.packets.append(pkt)


def chained(*emitters: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
    # fan-out: emit to multiple sinks in order.
    def _emit(pkt: dict[str, Any]) -> None:
        for e in emitters:
            e(pkt)
    return _emit
