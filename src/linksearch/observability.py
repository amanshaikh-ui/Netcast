"""Structured adapter observability for TikTok/Instagram (and shared conventions)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterObservation:
    query_used: str = ""
    adapter_name: str = ""
    runtime_region: str = "unknown"
    visible_results_count: int = 0
    network_payload_count: int = 0
    candidates_extracted: int = 0
    candidates_rejected: int = 0
    rejection_reason: str = ""
    seeds_expanded: int = 0
    retry_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "query_used": self.query_used,
            "adapter_name": self.adapter_name,
            "runtime_region": self.runtime_region,
            "visible_results_count": self.visible_results_count,
            "network_payload_count": self.network_payload_count,
            "candidates_extracted": self.candidates_extracted,
            "candidates_rejected": self.candidates_rejected,
            "rejection_reason": self.rejection_reason,
            "seeds_expanded": self.seeds_expanded,
            "retry_count": self.retry_count,
        }
        if self.extra:
            d["extra"] = self.extra
        return d
