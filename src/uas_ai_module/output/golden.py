"""Golden-output normalization and comparison helpers.

Replay regression needs stable comparisons while runtime packets contain expected
volatile fields such as timestamps, latency, and staleness counters. These
helpers normalize only those volatile fields and leave safety-critical content
intact.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


VOLATILE_HEALTH_FIELDS = {
    "latency_ms",
    "camera_stale_ms",
    "telemetry_stale_ms",
    "temperature_c",
    "power_w",
}


def normalize_advisory_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic copy of an advisory packet for golden comparison."""

    normalized = deepcopy(packet)
    normalized["timestamp_utc"] = "<normalized>"
    health = normalized.get("health")
    if isinstance(health, dict):
        for field in VOLATILE_HEALTH_FIELDS:
            if field in health:
                health[field] = "<normalized>"
        warnings = health.get("warnings")
        if isinstance(warnings, list):
            health["warnings"] = [_normalize_warning(str(item)) for item in warnings]
    return normalized


def normalize_packets(packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_advisory_packet(packet) for packet in packets]


def compare_packets(actual: list[dict[str, Any]], expected: list[dict[str, Any]]) -> list[str]:
    """Compare normalized packets and return human-readable mismatch messages."""

    actual_norm = normalize_packets(actual)
    expected_norm = normalize_packets(expected)
    if actual_norm == expected_norm:
        return []
    messages: list[str] = []
    if len(actual_norm) != len(expected_norm):
        messages.append(f"packet count mismatch: actual={len(actual_norm)} expected={len(expected_norm)}")
    for idx, (actual_packet, expected_packet) in enumerate(zip(actual_norm, expected_norm)):
        if actual_packet != expected_packet:
            messages.append(f"packet {idx} mismatch")
            if actual_packet.get("frame_id") != expected_packet.get("frame_id"):
                messages.append(
                    f"packet {idx} frame_id: actual={actual_packet.get('frame_id')} expected={expected_packet.get('frame_id')}"
                )
            if actual_packet.get("detections") != expected_packet.get("detections"):
                messages.append(f"packet {idx} detections differ")
            if actual_packet.get("health", {}).get("status") != expected_packet.get("health", {}).get("status"):
                messages.append(
                    f"packet {idx} health.status: actual={actual_packet.get('health', {}).get('status')} "
                    f"expected={expected_packet.get('health', {}).get('status')}"
                )
    return messages


def _normalize_warning(value: str) -> str:
    if value.startswith("stale_frame:"):
        return "stale_frame: <normalized> ms"
    if value.startswith("stale_telemetry:"):
        return "stale_telemetry: <normalized> ms"
    if "dropped" in value:
        return value
    return value
