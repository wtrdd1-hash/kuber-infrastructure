"""
Host Root Execution & Remote Control Service.
Enters NixOS host PID 1 root namespace using nsenter.
Full root privileges for shell commands, filesystem, systemctl, and kubectl.
"""
import os
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

AUDIT_LOG_HOST = "/host/var/log/gpt-audit.log"
AUDIT_LOG_LOCAL = "/var/log/gpt-audit.log"

NIXOS_ENV_PREFIX = (
    "export PATH=/run/current-system/sw/bin:/nix/var/nix/profiles/default/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH; export KUBECONFIG=/etc/kubernetes/admin.conf:/home/wtrdd/.kube/config; "
    "[ -f /etc/set-environment ] && . /etc/set-environment; "
)


def _log_audit(command: str, exit_code: int, caller: str = "chatgpt", duration_ms: float = 0.0):
    timestamp = datetime.now().isoformat()
    entry = f"[{timestamp}] [caller={caller}] [duration={duration_ms:.1f}ms] [exit={exit_code}] cmd: {command}\n"
    for log_path in [AUDIT_LOG_HOST, AUDIT_LOG_LOCAL]:
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry)
            break
        except Exception:
            continue


def run_host_command(
    command: str,
    timeout: int = 60,
    background: bool = False,
    caller: str = "chatgpt",
) -> Dict[str, Any]:
    """
    Executes a shell command directly in the host NixOS PID 1 root namespace.
    """
    start_time = time.time()
    wrapped_command = f"{NIXOS_ENV_PREFIX}{command}"

    nsenter_cmd = [
        "nsenter",
        "-t", "1",
        "-m", "-u", "-i", "-n", "-p",
        "--",
        "/run/current-system/sw/bin/bash",
        "-c",
    ]

    if background:
        log_file = f"/tmp/mcp_bg_{int(start_time)}.log"
        bg_shell_cmd = f"nohup /run/current-system/sw/bin/bash -c {wrapped_command!r} > {log_file} 2>&1 & echo $!"
        full_cmd = nsenter_cmd + [bg_shell_cmd]
        try:
            proc = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            pid = proc.stdout.strip()
            duration = (time.time() - start_time) * 1000
            _log_audit(command, proc.returncode, caller=caller, duration_ms=duration)
            return {
                "success": proc.returncode == 0,
                "background": True,
                "pid": pid,
                "log_file": log_file,
                "message": f"Command started in background with PID {pid}. Logs at {log_file}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    full_cmd = nsenter_cmd + [wrapped_command]
    try:
        proc = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = (time.time() - start_time) * 1000
        _log_audit(command, proc.returncode, caller=caller, duration_ms=duration)
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": round(duration, 2),
        }
    except subprocess.TimeoutExpired:
        _log_audit(command, -1, caller=caller, duration_ms=(timeout * 1000))
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
            "exit_code": -1,
        }
    except Exception as e:
        _log_audit(command, -2, caller=caller, duration_ms=0)
        return {"success": False, "error": str(e), "exit_code": -2}


def read_host_file(filepath: str, max_lines: int = 500) -> Dict[str, Any]:
    """Reads a file from the host filesystem with root privileges."""
    cmd = f"head -n {max_lines} {filepath!r}"
    res = run_host_command(cmd, timeout=10)
    if res.get("success"):
        return {
            "success": True,
            "filepath": filepath,
            "content": res.get("stdout", ""),
            "lines_shown": max_lines,
        }
    return {
        "success": False,
        "filepath": filepath,
        "error": res.get("stderr") or res.get("error"),
    }


def write_host_file(filepath: str, content: str, make_backup: bool = True) -> Dict[str, Any]:
    """Writes content to a host file with root privileges, optionally creating a .bak backup."""
    import tempfile
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        backup_cmd = f"if [ -f {filepath!r} ]; then cp {filepath!r} {filepath!r}.bak; fi && " if make_backup else ""
        move_cmd = f"{backup_cmd}cp /host{tmp_path} {filepath!r} && rm -f /host{tmp_path}"
        res = run_host_command(move_cmd, timeout=15)

        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        if res.get("success"):
            return {
                "success": True,
                "filepath": filepath,
                "bytes_written": len(content.encode("utf-8")),
                "backup_created": make_backup,
            }
        return {
            "success": False,
            "filepath": filepath,
            "error": res.get("stderr") or res.get("error"),
        }
    except Exception as e:
        return {"success": False, "filepath": filepath, "error": str(e)}


def manage_system_service(service_name: str, action: str) -> Dict[str, Any]:
    """Manages systemd services (status, start, stop, restart, reload, is-active) on host."""
    valid_actions = ["status", "start", "stop", "restart", "reload", "enable", "disable", "is-active"]
    if action not in valid_actions:
        return {"success": False, "error": f"Invalid action. Choose from: {valid_actions}"}
    return run_host_command(f"systemctl {action} {service_name}", timeout=30)


def manage_k8s(command: str) -> Dict[str, Any]:
    """Runs a kubectl command on the host with root privileges."""
    return run_host_command(f"kubectl {command}", timeout=30)
