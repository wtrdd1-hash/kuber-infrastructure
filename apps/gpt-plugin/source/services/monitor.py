import datetime
import os
import platform
import subprocess
import time
from typing import Any, Dict, List
import psutil


def get_uptime_human(seconds: float) -> str:
    """초 단위의 업타임을 일, 시, 분, 초 문자열로 변환합니다."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    parts = []
    if d > 0:
        parts.append(f"{d}일")
    if h > 0:
        parts.append(f"{h}시간")
    if m > 0:
        parts.append(f"{m}분")
    parts.append(f"{s}초")
    return " ".join(parts)


def get_system_overview() -> Dict[str, Any]:
    """미니 PC 기본 시스템 개요를 반환합니다."""
    boot_timestamp = psutil.boot_time()
    uptime_sec = time.time() - boot_timestamp

    return {
        "hostname": platform.node(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "uptime_seconds": round(uptime_sec, 1),
        "uptime_human": get_uptime_human(uptime_sec),
        "boot_time": datetime.datetime.fromtimestamp(boot_timestamp, tz=datetime.timezone.utc).isoformat(),
        "current_time": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "python_version": platform.python_version(),
    }


def get_system_metrics() -> Dict[str, Any]:
    """CPU, 메모리, 디스크, 네트워크 사용량 메트릭을 반환합니다."""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)
    per_cpu = psutil.cpu_percent(interval=None, percpu=True)
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)

    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disk
    disk = psutil.disk_usage("/")

    # Network
    net = psutil.net_io_counters()

    return {
        "cpu": {
            "percent_total": cpu_percent,
            "cores_physical": psutil.cpu_count(logical=False) or 1,
            "cores_logical": psutil.cpu_count(logical=True) or 1,
            "load_average_1m_5m_15m": [round(x, 2) for x in load_avg],
            "per_core_percent": per_cpu,
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent,
        },
        "swap": {
            "total_gb": round(swap.total / (1024**3), 2),
            "used_gb": round(swap.used / (1024**3), 2),
            "free_gb": round(swap.free / (1024**3), 2),
            "percent": swap.percent,
        },
        "disk_root": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent,
        },
        "network": {
            "sent_mb": round(net.bytes_sent / (1024**2), 2),
            "recv_mb": round(net.bytes_recv / (1024**2), 2),
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
        },
    }


def get_top_processes(limit: int = 10, sort_by: str = "memory") -> List[Dict[str, Any]]:
    """리소스 점유율 상위 프로세스 목록을 반환합니다."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "status"]):
        try:
            info = p.info
            info["cpu_percent"] = round(info.get("cpu_percent") or 0.0, 1)
            info["memory_percent"] = round(info.get("memory_percent") or 0.0, 1)
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if sort_by == "cpu":
        procs.sort(key=lambda x: x.get("cpu_percent", 0.0), reverse=True)
    else:
        procs.sort(key=lambda x: x.get("memory_percent", 0.0), reverse=True)

    return procs[: max(1, min(limit, 50))]


def get_recent_logs(lines: int = 30) -> List[str]:
    """최근 시스템 저널(journalctl) 로그 목록을 반환합니다."""
    safe_lines = max(5, min(lines, 100))
    try:
        res = subprocess.run(
            ["journalctl", "-n", str(safe_lines), "--no-pager", "-o", "short-iso"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout:
            return [line for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        pass

    # journalctl 실패 시 dmesg 폴백
    try:
        res = subprocess.run(["dmesg"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout:
            lines_list = [l for l in res.stdout.splitlines() if l.strip()]
            return lines_list[-safe_lines:]
    except Exception as e:
        return [f"로그 수집 실패: {str(e)}"]

    return ["시스템 로그가 비어 있거나 접근 권한이 없습니다."]
