import asyncio
from contextlib import asynccontextmanager
import json
import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from app.services import cloudflare_dns, executor
from app.services.ddns import ddns_background_loop, get_ddns_status, sync_ddns
from app.services.k8s import get_k8s_summary
from app.services.monitor import (
    get_recent_logs,
    get_system_metrics,
    get_system_overview,
    get_top_processes,
)

# 1. FastMCP 인스턴스 (ChatGPT Custom MCP Plugin 지원)
mcp = FastMCP(
    name="MiniPC Root Operations & Cloudflare Manager",
    instructions=(
        "미니 PC의 완전한 root 셸 명령어 실행(execute_command), 파일시스템 읽기/쓰기(read_file, write_file), "
        "systemctl 서비스 제어(manage_service), kubectl 클러스터 제어(manage_k8s) 및 "
        "실시간 하드웨어 모니터링, Cloudflare DNS/DDNS 자동 갱신을 수행하는 통합 원격 관리 도구입니다."
    ),
)
# 프록시 도메인 요청 허용
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False
)

# --- MCP 모니터링 도구 ---
@mcp.tool(name="get_system_overview", description="미니 PC 호스트명, OS(NixOS), 커널, 부팅 시각, 누적 업타임을 조회합니다.")
async def mcp_system_overview() -> str:
    return json.dumps(await asyncio.to_thread(get_system_overview), ensure_ascii=False)


@mcp.tool(name="get_system_metrics", description="CPU 전체/코어별 사용률, RAM/Swap 점유율, 디스크 잔여량, 네트워크 I/O 통계를 조회합니다.")
async def mcp_system_metrics() -> str:
    return json.dumps(await asyncio.to_thread(get_system_metrics), ensure_ascii=False)


@mcp.tool(name="get_top_processes", description="메모리 또는 CPU 점유율이 높은 상위 프로세스 목록을 조회합니다. limit(기본 10), sort_by('memory' 또는 'cpu')")
async def mcp_top_processes(limit: int = 10, sort_by: str = "memory") -> str:
    return json.dumps(await asyncio.to_thread(get_top_processes, limit=limit, sort_by=sort_by), ensure_ascii=False)


@mcp.tool(name="get_system_logs", description="최근 systemd journalctl 또는 dmesg 시스템 로그를 조회합니다. lines(기본 30)")
async def mcp_system_logs(lines: int = 30) -> str:
    return json.dumps({"logs": await asyncio.to_thread(get_recent_logs, lines=lines)}, ensure_ascii=False)


@mcp.tool(name="get_k8s_summary", description="미니 PC의 Kubernetes 클러스터 노드 및 파드 구동 상태를 요약 조회합니다.")
async def mcp_k8s_summary() -> str:
    return json.dumps(await asyncio.to_thread(get_k8s_summary), ensure_ascii=False)


# --- MCP DNS 및 DDNS 관리 도구 ---
@mcp.tool(
    name="create_dns_record",
    description=(
        "Cloudflare에 새로운 DNS 레코드(A, CNAME, TXT 등)를 생성합니다. "
        "name: 서브도메인명(예: 'sub' 또는 'sub.easy-scraping.com'), "
        "record_type: 'A', 'CNAME', 'TXT' 등, "
        "content: IP 주소 또는 대상 호스트, "
        "proxied: Cloudflare 프록시(주황색 구름) 사용 여부 (생략 시 스마트 자동 결정)"
    ),
)
def mcp_create_dns_record(
    name: str,
    record_type: str,
    content: str,
    proxied: Optional[bool] = None,
) -> str:
    try:
        res = cloudflare_dns.create_dns_record(
            name=name, record_type=record_type, content=content, proxied=proxied
        )
        return json.dumps({"success": True, "record": res}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(name="list_dns_records", description="Cloudflare에 등록된 DNS 레코드 목록을 조회합니다. record_type(선택: 'A', 'CNAME', 'TXT' 등)")
def mcp_list_dns_records(record_type: Optional[str] = None) -> str:
    try:
        records = cloudflare_dns.list_dns_records(record_type=record_type)
        return json.dumps({"count": len(records), "records": records}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(name="get_ddns_status", description="미니 PC의 현재 외부 공인 IP와 DDNS 자동 갱신 데몬 상태를 조회합니다.")
def mcp_get_ddns_status() -> str:
    return json.dumps(get_ddns_status(), ensure_ascii=False)


@mcp.tool(
    name="trigger_ddns_sync",
    description="미니 PC의 외부 공인 IP를 즉시 확인하고, 변경되었거나 force=True일 때 Cloudflare DNS A 레코드들을 일괄 동기화합니다.",
)
def mcp_trigger_ddns_sync(force: bool = False) -> str:
    try:
        res = sync_ddns(force=force)
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# --- MCP 호스트 완전 제어 (Root Shell, File, Service, K8s) 도구 ---
@mcp.tool(
    name="execute_command",
    description=(
        "미니 PC 호스트 NixOS에서 root 권한으로 임의의 bash 셸 명령어를 실행합니다. "
        "command: 실행할 셸 명령어(예: 'systemctl status sshd', 'reboot', 'docker ps', 'cat /etc/nixos/configuration.nix'), "
        "timeout: 최대 실행 대기 초 (기본 60초), "
        "background: 백그라운드 비동기 실행 여부 (빌드/다운로드 등 긴 작업 시 True)"
    ),
)
async def mcp_execute_command(command: str, timeout: int = 60, background: bool = False) -> str:
    res = await asyncio.to_thread(executor.run_host_command, command=command, timeout=timeout, background=background)
    return json.dumps(res, ensure_ascii=False)


@mcp.tool(
    name="exec_command",
    description="미니 PC 호스트 NixOS에서 root 권한으로 임의의 bash 셸 명령어를 실행합니다. command: 실행할 명령어 (execute_command의 별칭)",
)
async def mcp_exec_command(command: str, timeout: int = 60, background: bool = False) -> str:
    res = await asyncio.to_thread(executor.run_host_command, command=command, timeout=timeout, background=background)
    return json.dumps(res, ensure_ascii=False)


@mcp.tool(
    name="shell",
    description="미니 PC 호스트 NixOS에서 root 권한으로 임의의 bash 셸 명령어를 실행합니다. command: 실행할 명령어 (execute_command의 별칭)",
)
async def mcp_shell(command: str, timeout: int = 60, background: bool = False) -> str:
    res = await asyncio.to_thread(executor.run_host_command, command=command, timeout=timeout, background=background)
    return json.dumps(res, ensure_ascii=False)



@mcp.tool(
    name="read_file",
    description="미니 PC 호스트 시스템의 파일 내용을 root 권한으로 읽어옵니다. filepath: 호스트 절대경로, max_lines: 최대 읽을 라인 수(기본 500)",
)
async def mcp_read_file(filepath: str, max_lines: int = 500) -> str:
    res = await asyncio.to_thread(executor.read_host_file, filepath=filepath, max_lines=max_lines)
    return json.dumps(res, ensure_ascii=False)


@mcp.tool(
    name="write_file",
    description="미니 PC 호스트 시스템에 파일을 root 권한으로 생성하거나 덮어씁니다. filepath: 호스트 절대경로, content: 파일 내용, make_backup: 기존 파일 자동 .bak 백업 여부(기본 True)",
)
async def mcp_write_file(filepath: str, content: str, make_backup: bool = True) -> str:
    res = await asyncio.to_thread(executor.write_host_file, filepath=filepath, content=content, make_backup=make_backup)
    return json.dumps(res, ensure_ascii=False)


@mcp.tool(
    name="manage_service",
    description="미니 PC 호스트의 systemd 서비스를 root 권한으로 제어합니다. service_name: 서비스 이름(예: 'sshd', 'caddy', 'k3s'), action: 'status' | 'start' | 'stop' | 'restart' | 'reload' | 'is-active'",
)
async def mcp_manage_service(service_name: str, action: str) -> str:
    res = await asyncio.to_thread(executor.manage_system_service, service_name=service_name, action=action)
    return json.dumps(res, ensure_ascii=False)


@mcp.tool(
    name="manage_k8s",
    description="미니 PC 호스트 클러스터에서 kubectl 명령어를 root 권한으로 실행합니다. command: kubectl 하위 인자(예: 'get pods -A', 'logs -n gpt-plugin <pod>', 'apply -f <file>')",
)
async def mcp_manage_k8s(command: str) -> str:
    res = await asyncio.to_thread(executor.manage_k8s, command=command)
    return json.dumps(res, ensure_ascii=False)



# 2. FastAPI Lifespan (DDNS 백그라운드 워커 자동 구동)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 테스트/격리 환경에서는 DDNS 외부 변경을 명시적으로 끌 수 있습니다.
    ddns_enabled = os.getenv("DDNS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    ddns_task = asyncio.create_task(ddns_background_loop()) if ddns_enabled else None
    yield
    if ddns_task is not None:
        ddns_task.cancel()
        try:
            await ddns_task
        except asyncio.CancelledError:
            pass


# 3. FastAPI 메인 앱
app = FastAPI(
    title="MiniPC Operations & DDNS Cloudflare Manager",
    description="ChatGPT Custom Action & MCP Server for MiniPC monitoring and dynamic DNS automation.",
    version="1.1.0",
    lifespan=lifespan,
    servers=[
        {"url": "https://gpt.easy-scraping.com", "description": "Production Domain"},
        {"url": "https://test.easy-scraping.com/mcp", "description": "Subdomain Route"},
        {"url": "http://127.0.0.1:8000", "description": "Local Direct"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REST 시스템 엔드포인트 ---
@app.get("/health", tags=["Health"], summary="서버 헬스체크", operation_id="checkHealth")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "message": "MiniPC GPT Plugin & DDNS Server is running smoothly"}


@app.get("/system/overview", tags=["System"], summary="미니 PC 시스템 개요", operation_id="getSystemOverview")
def system_overview() -> Dict[str, Any]:
    return get_system_overview()


@app.get("/system/metrics", tags=["System"], summary="CPU, 메모리, 디스크 실시간 메트릭", operation_id="getSystemMetrics")
def system_metrics() -> Dict[str, Any]:
    return get_system_metrics()


@app.get("/system/processes", tags=["Processes"], summary="상위 프로세스 목록", operation_id="getTopProcesses")
def top_processes(
    limit: int = Query(10, ge=1, le=50, description="반환할 상위 프로세스 개수"),
    sort_by: str = Query("memory", pattern="^(memory|cpu)$", description="정렬 기준"),
) -> List[Dict[str, Any]]:
    return get_top_processes(limit=limit, sort_by=sort_by)


@app.get("/system/logs", tags=["Logs"], summary="최근 시스템 저널 로그", operation_id="getSystemLogs")
def system_logs(lines: int = Query(30, ge=5, le=100, description="조회할 로그 라인 수")) -> Dict[str, Any]:
    return {"logs": get_recent_logs(lines=lines)}


@app.get("/system/k8s", tags=["Kubernetes"], summary="Kubernetes 클러스터 상태", operation_id="getK8sSummary")
def k8s_summary() -> Dict[str, Any]:
    return get_k8s_summary()


# --- REST DNS 및 DDNS 관리 엔드포인트 ---
class CreateDnsRequest(BaseModel):
    name: str = Field(..., description="서브도메인 이름 (예: 'api', 'sub', 'test')")
    record_type: str = Field("A", description="레코드 타입 ('A', 'CNAME', 'TXT' 등)")
    content: str = Field(..., description="IP 주소 또는 대상 호스트명")
    proxied: Optional[bool] = Field(None, description="Cloudflare 프록시 여부 (생략 시 자동 결정)")
    ttl: int = Field(1, ge=1, description="TTL (1 = 자동)")


@app.get("/dns/records", tags=["DNS"], summary="Cloudflare DNS 레코드 목록 조회", operation_id="listDnsRecords")
def api_list_dns(record_type: Optional[str] = None, name: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        return cloudflare_dns.list_dns_records(record_type=record_type, name=name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dns/records", tags=["DNS"], summary="신규 DNS 레코드 생성", operation_id="createDnsRecord")
def api_create_dns(req: CreateDnsRequest) -> Dict[str, Any]:
    try:
        return cloudflare_dns.create_dns_record(
            name=req.name,
            record_type=req.record_type,
            content=req.content,
            proxied=req.proxied,
            ttl=req.ttl,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/dns/records/{record_id}", tags=["DNS"], summary="DNS 레코드 삭제", operation_id="deleteDnsRecord")
def api_delete_dns(record_id: str) -> Dict[str, Any]:
    try:
        return cloudflare_dns.delete_dns_record(record_id=record_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/ddns/status", tags=["DDNS"], summary="DDNS 자동 갱신 데몬 상태 조회", operation_id="getDdnsStatus")
def api_ddns_status() -> Dict[str, Any]:
    return get_ddns_status()


@app.post("/ddns/sync", tags=["DDNS"], summary="DDNS 즉시 수동 동기화", operation_id="syncDdns")
def api_ddns_sync(force: bool = Query(False, description="IP 변경 여부와 상관없이 강제 동기화")) -> Dict[str, Any]:
    return sync_ddns(force=force)


# 4. FastMCP SSE 엔드포인트 마운트 및 루트('/') 지원
from starlette.requests import Request
from starlette.routing import Route

sse_app = mcp.sse_app()
# sse_app 내부의 sse_endpoint(GET) 및 handle_post_message(POST) 핸들러 추출
sse_endpoint = None
post_handler = None
for r in sse_app.routes:
    if getattr(r, "methods", None) and "GET" in r.methods:
        sse_endpoint = r.endpoint
    elif hasattr(r, "app"):
        post_handler = r.app

# 루트('/') 경로로 접속해도 즉시 SSE 연결이 성립되도록 FastAPI 핸들러 직접 등록
if sse_endpoint:
    @app.get("/", include_in_schema=False)
    @app.head("/", include_in_schema=False)
    async def root_sse(request: Request):
        return await sse_endpoint(request)

    @app.get("/sse", include_in_schema=False)
    @app.head("/sse", include_in_schema=False)
    async def direct_sse(request: Request):
        return await sse_endpoint(request)

if post_handler:
    @app.post("/", include_in_schema=False)
    async def root_post(request: Request):
        return await post_handler(request.scope, request.receive, request._send)

# Starlette sse_app 마운트
app.mount("/mcp", sse_app)
app.mount("/", sse_app)
