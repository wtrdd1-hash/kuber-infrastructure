import os
from pathlib import Path

SECRET_ENV_FILE = Path(os.getenv("MCP_SECRET_ENV_FILE", "/run/secrets/cloudflare.env"))

def _load_secret_env() -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for raw in SECRET_ENV_FILE.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return values

_SECRET_ENV = _load_secret_env()

def _setting(name: str, default: str = "") -> str:
    return os.getenv(name) or _SECRET_ENV.get(name, default)


# Cloudflare 인증 및 도메인 설정
CF_EMAIL = _setting("CF_EMAIL")
CF_API_KEY = _setting("CF_API_KEY")
CF_ZONE_ID = _setting("CF_ZONE_ID")
CF_DOMAIN = _setting("CF_DOMAIN")
CF_ACCOUNT_ID = _setting("CF_ACCOUNT_ID")
CF_TUNNEL_ID = _setting("CF_TUNNEL_ID")

# DDNS 주기 (초 단위, 기본 60초)
DDNS_INTERVAL_SECONDS = int(os.getenv("DDNS_INTERVAL_SECONDS", "60"))
DDNS_DOMAINS = [
    item.strip().lower()
    for item in _setting("DDNS_DOMAINS", "").split(",")
    if item.strip()
]
DDNS_UPDATE_SPF = os.getenv("DDNS_UPDATE_SPF", "false").strip().lower() in {"1", "true", "yes", "on"}

# IP 캐시 파일 경로
DATA_DIR = Path("/workspace/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
IP_CACHE_FILE = DATA_DIR / "last_public_ip.txt"
DDNS_LOG_FILE = DATA_DIR / "ddns_history.json"
