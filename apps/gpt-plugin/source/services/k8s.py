import subprocess
from typing import Any, Dict


def get_k8s_summary() -> Dict[str, Any]:
    """미니 PC 내의 Kubernetes 노드 및 실행 중인 파드 요약 상태를 반환합니다."""
    result: Dict[str, Any] = {
        "status": "unknown",
        "nodes": [],
        "pods_summary": {},
        "raw_message": "",
    }

    try:
        # 노드 상태 확인
        node_res = subprocess.run(
            ["kubectl", "get", "nodes", "--no-headers"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if node_res.returncode == 0:
            result["status"] = "available"
            result["nodes"] = [
                line.split()[0] + f" ({line.split()[1]})"
                for line in node_res.stdout.splitlines()
                if line.strip()
            ]
        else:
            result["status"] = "unavailable"
            result["raw_message"] = node_res.stderr.strip()
            return result

        # 파드 상태 요약
        pod_res = subprocess.run(
            ["kubectl", "get", "pods", "-A", "--no-headers"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if pod_res.returncode == 0:
            pod_lines = [l for l in pod_res.stdout.splitlines() if l.strip()]
            status_counts: Dict[str, int] = {}
            for line in pod_lines:
                parts = line.split()
                if len(parts) >= 4:
                    status = parts[3]
                    status_counts[status] = status_counts.get(status, 0) + 1

            result["pods_summary"] = {
                "total_pods": len(pod_lines),
                "by_status": status_counts,
            }
    except Exception as e:
        result["status"] = "error"
        result["raw_message"] = str(e)

    return result
