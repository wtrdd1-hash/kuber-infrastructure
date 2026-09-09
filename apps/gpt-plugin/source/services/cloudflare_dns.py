import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core import config

logger = logging.getLogger("cloudflare_dns")
BASE_URL = f"https://api.cloudflare.com/client/v4/zones/{config.CF_ZONE_ID}/dns_records"


def get_headers() -> Dict[str, str]:
    return {
        "X-Auth-Email": config.CF_EMAIL,
        "X-Auth-Key": config.CF_API_KEY,
        "Content-Type": "application/json",
    }


def normalize_record_name(name: str) -> str:
    """FQDN(도메인 전체 이름) 형식으로 정규화합니다."""
    name = name.strip().lower()
    if not name.endswith(config.CF_DOMAIN):
        name = f"{name}.{config.CF_DOMAIN}"
    return name


def list_dns_records(
    record_type: Optional[str] = None, name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Cloudflare에 등록된 DNS 레코드 목록을 반환합니다."""
    params: Dict[str, Any] = {"per_page": 100}
    if record_type:
        params["type"] = record_type.upper()
    if name:
        params["name"] = normalize_record_name(name)

    with httpx.Client(timeout=10.0) as client:
        res = client.get(BASE_URL, headers=get_headers(), params=params)
        data = res.json()
        if not data.get("success"):
            error_msg = "; ".join([e.get("message", "") for e in data.get("errors", [])])
            raise RuntimeError(f"Cloudflare DNS 조회 실패: {error_msg}")
        return data.get("result", [])


def create_dns_record(
    name: str,
    record_type: str,
    content: str,
    proxied: Optional[bool] = None,
    ttl: int = 1,
) -> Dict[str, Any]:
    """새로운 DNS 레코드(A, CNAME, TXT 등)를 생성합니다."""
    full_name = normalize_record_name(name)
    rec_type = record_type.upper()

    # 스마트 프록시 기본값 결정
    if proxied is None:
        if rec_type in ["A", "AAAA", "CNAME"]:
            # SSH, 게임, 마인크래프트, NAS 등 전용 포트 도메인은 프록시 해제
            if any(k in full_name for k in ["ssh", "game", "mc", "nas", "pvp", "direct", "tcp", "udp"]):
                proxied = False
            else:
                proxied = True
        else:
            proxied = False

    payload: Dict[str, Any] = {
        "type": rec_type,
        "name": full_name,
        "content": content.strip(),
        "ttl": ttl,
    }
    # CNAME, A, AAAA에만 proxied 속성 적용 가능
    if rec_type in ["A", "AAAA", "CNAME"]:
        payload["proxied"] = bool(proxied)

    with httpx.Client(timeout=10.0) as client:
        res = client.post(BASE_URL, headers=get_headers(), json=payload)
        data = res.json()
        if not data.get("success"):
            error_msg = "; ".join([e.get("message", "") for e in data.get("errors", [])])
            raise RuntimeError(f"DNS 레코드 생성 실패: {error_msg}")
        return data.get("result", {})


def update_dns_record(
    record_id: str,
    name: str,
    record_type: str,
    content: str,
    proxied: bool = False,
    ttl: int = 1,
) -> Dict[str, Any]:
    """기존 DNS 레코드의 대상 IP나 호스트를 업데이트합니다."""
    rec_type = record_type.upper()
    payload: Dict[str, Any] = {
        "type": rec_type,
        "name": normalize_record_name(name),
        "content": content.strip(),
        "ttl": ttl,
    }
    if rec_type in ["A", "AAAA", "CNAME"]:
        payload["proxied"] = bool(proxied)

    url = f"{BASE_URL}/{record_id}"
    with httpx.Client(timeout=10.0) as client:
        res = client.put(url, headers=get_headers(), json=payload)
        data = res.json()
        if not data.get("success"):
            error_msg = "; ".join([e.get("message", "") for e in data.get("errors", [])])
            raise RuntimeError(f"DNS 레코드 수정 실패: {error_msg}")
        return data.get("result", {})


def delete_dns_record(record_id: str) -> Dict[str, Any]:
    """지정한 ID의 DNS 레코드를 삭제합니다."""
    url = f"{BASE_URL}/{record_id}"
    with httpx.Client(timeout=10.0) as client:
        res = client.delete(url, headers=get_headers())
        data = res.json()
        if not data.get("success"):
            error_msg = "; ".join([e.get("message", "") for e in data.get("errors", [])])
            raise RuntimeError(f"DNS 레코드 삭제 실패: {error_msg}")
        return data.get("result", {})
