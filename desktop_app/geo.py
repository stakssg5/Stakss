from __future__ import annotations

import ipaddress
import re
from typing import Any, Dict, Optional

import requests

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.(?:[A-Za-z]{2,63}|[A-Za-z0-9-]{2,63}\.[A-Za-z]{2,63})$")


def is_ip(target: str) -> bool:
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False


def is_domain(target: str) -> bool:
    return bool(DOMAIN_RE.search(target))


def geolocate(target: str, endpoint_template: str, api_key: Optional[str] = None, timeout_s: int = 10) -> Dict[str, Any]:
    target = target.strip()
    if not target:
        raise ValueError("target is empty")
    # ipapi can accept IP or domain; keep simple validation
    url = endpoint_template.format(target=target)
    headers = {"User-Agent": "ForensicSearch/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(url, headers=headers, timeout=timeout_s)
    resp.raise_for_status()
    data = resp.json()
    # Normalize common fields
    result = {
        "ip": data.get("ip"),
        "city": data.get("city"),
        "region": data.get("region") or data.get("region_code") or data.get("region_name"),
        "country": data.get("country_name") or data.get("country"),
        "country_code": data.get("country") or data.get("country_code"),
        "postal": data.get("postal"),
        "latitude": data.get("latitude") or data.get("lat"),
        "longitude": data.get("longitude") or data.get("lon") or data.get("lng"),
        "timezone": data.get("timezone"),
        "org": data.get("org") or data.get("asn"),
        "error": None,
    }
    # Some providers return 'error' field
    if data.get("error"):
        result["error"] = data.get("reason") or data.get("message") or str(data.get("error"))
    return result
