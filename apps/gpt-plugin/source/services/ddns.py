import asyncio
import datetime
import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

from app.core import config
from app.services import cloudflare_dns

logger = logging.getLogger("ddns_daemon")

# 메모리 상의 최근 상태 캐시
_latest_status: Dict[str, Any] = {
    "last_checked": None,
    "last_ip": None,
    "last_changed": None,
    "status": "initializing",
    "updated_count": 0,
    "error": None,
}


def fetch_public_ip() -> str:
    """외부 공인 IP를 복수의 신뢰 소스를 통해 확인합니다."""
    sources = [
        ("https://api.ipify.org", lambda t: t.strip()),
        ("https://cloudflare.com/cdn-cgi/trace", lambda t: re.search(r"ip=([0-9.]+)", t).group(1)),
        ("https://icanhazip.com", lambda t: t.strip()),
    ]
    with httpx.Client(timeout=5.0) as client:
        for url, parser in sources:
            try:
                res = client.get(url)
                if res.status_code == 200:
                    ip = parser(res.text)
                    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                        return ip
            except Exception:
                continue
    raise RuntimeError("외부 공인 IP를 확인할 수 없습니다.")


def get_cached_ip() -> Optional[str]:
    """이전에 저장된 공인 IP를 읽어옵니다."""
    if config.IP_CACHE_FILE.exists():
        try:
            ip = config.IP_CACHE_FILE.read_text().strip()
            if ip:
                return ip
        except Exception:
            pass
    return None


def save_cached_ip(ip: str) -> None:
    """새 공인 IP를 로컬 파일에 캐시합니다."""
    try:
        config.IP_CACHE_FILE.write_text(ip)
    except Exception as e:
        logger.error(f"IP 캐시 파일 저장 실패: {e}")


def sync_ddns(force: bool = False) -> Dict[str, Any]:
    """현재 공인 IP를 확인하고, 변경되었거나 강제 요청 시 Cloudflare DNS를 갱신합니다."""
    global _latest_status
    now_iso = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    _latest_status["last_checked"] = now_iso

    try:
        current_ip = fetch_public_ip()
    except Exception as e:
        _latest_status["status"] = "error"
        _latest_status["error"] = str(e)
        logger.error(f"공인 IP 확인 실패: {e}")
        return {"success": False, "error": str(e)}

    cached_ip = get_cached_ip()
    ip_changed = cached_ip != current_ip

    result: Dict[str, Any] = {
        "timestamp": now_iso,
        "current_ip": current_ip,
        "previous_ip": cached_ip,
        "ip_changed": ip_changed,
        "force": force,
        "updated_records": [],
    }

    if not ip_changed and not force:
        _latest_status.update({
            "status": "in_sync",
            "last_ip": current_ip,
            "error": None,
        })
        result["message"] = f"IP 변경 없음 ({current_ip}). DNS가 최신 상태입니다."
        return result

    logger.info(f"==> DDNS 갱신 시작 (이전 IP: {cached_ip} -> 현재 IP: {current_ip}, 강제: {force})")

    # Cloudflare A 레코드 목록 조회
    try:
        records = cloudflare_dns.list_dns_records(record_type="A")
    except Exception as e:
        _latest_status["status"] = "error"
        _latest_status["error"] = str(e)
        return {"success": False, "error": f"DNS 목록 조회 실패: {e}"}

    updated_records = []
    failed_records = []

    # 이전 공인 IP를 직접 가리키는 모든 A 레코드 업데이트
    for rec in records:
        old_ip = rec.get("content")
        if not cached_ip or old_ip != cached_ip or old_ip == current_ip:
            continue
        try:
            cloudflare_dns.update_dns_record(
                record_id=rec["id"],
                name=rec["name"],
                record_type="A",
                content=current_ip,
                proxied=rec.get("proxied", False),
                ttl=rec.get("ttl", 1),
            )
            updated_records.append({
                "name": rec["name"],
                "old_ip": old_ip,
                "new_ip": current_ip,
                "proxied": rec.get("proxied", False),
            })
            logger.info(f"DNS 갱신 완료: {rec['name']} -> {current_ip}")
        except Exception as ex:
            failed_records.append({"name": rec["name"], "error": str(ex)})
            logger.error(f"DNS 갱신 실패 ({rec['name']}): {ex}")

    # SPF TXT 레코드의 ip4:<old_ip>도 새 공인 IP로 자동 갱신합니다.
    try:
        txt_records = cloudflare_dns.list_dns_records(record_type="TXT", name=config.CF_DOMAIN) if cached_ip else []
        for rec in txt_records:
            content = rec.get("content", "")
            if "v=spf1" in content and (cached_ip and f"ip4:{cached_ip}" in content):
                new_content = content.replace(f"ip4:{cached_ip}", f"ip4:{current_ip}")
                cloudflare_dns.update_dns_record(
                    record_id=rec["id"],
                    name=rec["name"],
                    record_type="TXT",
                    content=new_content,
                    ttl=rec.get("ttl", 1),
                )
                updated_records.append({
                    "name": rec["name"] + " (SPF TXT)",
                    "old_ip": cached_ip,
                    "new_ip": current_ip,
                })
                logger.info(f"SPF TXT 갱신 완료: {new_content}")
    except Exception as e:
        failed_records.append({"name": f"{config.CF_DOMAIN} (SPF TXT)", "error": str(e)})
        logger.error(f"SPF TXT 조회/갱신 실패: {e}")

    if failed_records:
        _latest_status.update({
            "status": "error",
            "last_ip": cached_ip,
            "updated_count": len(updated_records),
            "error": f"{len(failed_records)}개 DDNS 레코드 갱신 실패",
        })
        result["updated_records"] = updated_records
        result["failed_records"] = failed_records
        result["success"] = False
        return result

    # 모든 대상 레코드 갱신이 성공한 경우에만 캐시를 전진시켜 다음 주기 재시도를 보장합니다.
    save_cached_ip(current_ip)

    _latest_status.update({
        "status": "updated" if updated_records else "in_sync",
        "last_ip": current_ip,
        "last_changed": now_iso if ip_changed else _latest_status.get("last_changed"),
        "updated_count": len(updated_records),
        "error": None,
    })

    result["updated_records"] = updated_records
    result["message"] = f"DDNS 동기화 완료: {len(updated_records)}개 레코드 갱신됨."
    result["success"] = True
    return result


def get_ddns_status() -> Dict[str, Any]:
    """현재 DDNS 데몬의 상태 및 공인 IP 정보를 반환합니다."""
    global _latest_status
    cached = get_cached_ip()
    status = dict(_latest_status)
    status["cached_ip"] = cached
    status["check_interval_seconds"] = config.DDNS_INTERVAL_SECONDS
    status["mode"] = "all_A_records_matching_previous_public_ip"
    status["spf_update"] = True
    return status


async def ddns_background_loop() -> None:
    """백그라운드에서 설정된 주기(기본 60초)마다 공인 IP를 감지하고 자동 동기화합니다."""
    logger.info(f"DDNS 백그라운드 워커 시작됨 (감지 주기: {config.DDNS_INTERVAL_SECONDS}초)")
    # 초기 기동 시 1회 즉시 실행
    try:
        await asyncio.to_thread(sync_ddns, force=False)
    except Exception as e:
        logger.error(f"초기 DDNS 동기화 오류: {e}")

    while True:
        try:
            await asyncio.sleep(config.DDNS_INTERVAL_SECONDS)
            await asyncio.to_thread(sync_ddns, force=False)
        except asyncio.CancelledError:
            logger.info("DDNS 백그라운드 워커 중단됨.")
            break
        except Exception as e:
            logger.error(f"DDNS 백그라운드 루프 에러: {e}")
            await asyncio.sleep(10)
