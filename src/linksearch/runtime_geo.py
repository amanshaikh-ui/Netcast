"""Best-effort runtime region hint (for geo-aware warnings, e.g. India + social friction)."""

from __future__ import annotations

import os
import zoneinfo

from datetime import datetime


def get_runtime_region() -> str:
    forced = (os.environ.get("LINKSEARCH_RUNTIME_REGION") or "").strip().upper()
    if forced:
        return forced[:32]
    tz_name = os.environ.get("TZ") or ""
    if "Kolkata" in tz_name or tz_name in ("Asia/Kolkata", "Asia/Calcutta"):
        return "IN"
    try:
        local = datetime.now().astimezone().tzinfo
        if local is not None:
            key = getattr(local, "key", None)
            if key == "Asia/Kolkata":
                return "IN"
    except Exception:
        pass
    try:
        z = zoneinfo.ZoneInfo("Asia/Kolkata")
        if datetime.now(z).utcoffset() == datetime.now().astimezone().utcoffset():
            # Weak heuristic: same offset as India (not unique); only if TZ unset
            if not tz_name and not forced:
                return "UNKNOWN_IST_OFFSET"
    except Exception:
        pass
    return "UNKNOWN"


def india_geo_warning_message(region: str | None = None) -> str | None:
    r = region or get_runtime_region()
    if r == "IN" or r == "UNKNOWN_IST_OFFSET":
        return (
            "Runtime suggests India or IST-offset timezone: TikTok/Instagram public discovery "
            "can be unreliable (guest/login walls, rate limits). Prefer session cookies for IG "
            "when permitted; alternate query packs and DDG/Brave/CSE fallbacks remain enabled."
        )
    return None
