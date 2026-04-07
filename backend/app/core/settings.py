import os
from ipaddress import ip_network
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file(Path(__file__).resolve().parents[2] / ".env")


class Settings:
    github_token = os.getenv("GITHUB_TOKEN")
    github_client_id = os.getenv("GITHUB_CLIENT_ID", "Iv23lica2ffEV55D1BqG")
    github_app_id = os.getenv("GITHUB_APP_ID", "")
    github_app_private_key = os.getenv("GITHUB_APP_PRIVATE_KEY", "")
    github_api_base = os.getenv("GITHUB_API_BASE", "https://api.github.com")
    reviewer_config_dir = os.getenv("REVIEWER_CONFIG_DIR", "")
    reviewer_publish_github_token = os.getenv("REVIEWER_PUBLISH_GITHUB_TOKEN", "")
    reviewer_backend_api_base = os.getenv("REVIEWER_BACKEND_API_BASE", "").rstrip("/")
    backend_port = int(os.getenv("BACKEND_PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    stale_cache_ttl_seconds = int(os.getenv("STALE_CACHE_TTL_SECONDS", "43200"))
    analyze_window_seconds = int(os.getenv("ANALYZE_WINDOW_SECONDS", "60"))
    analyze_requests_per_window = int(os.getenv("ANALYZE_REQUESTS_PER_WINDOW", "6"))
    preview_window_seconds = int(os.getenv("PREVIEW_WINDOW_SECONDS", "60"))
    preview_requests_per_window = int(os.getenv("PREVIEW_REQUESTS_PER_WINDOW", "12"))
    request_history_max_keys = int(os.getenv("REQUEST_HISTORY_MAX_KEYS", "5000"))
    max_pr_commit_pages = int(os.getenv("MAX_PR_COMMIT_PAGES", "10"))
    database_url = os.getenv("DATABASE_URL")
    cors_allow_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOW_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]
    cors_allow_origin_regex = os.getenv("CORS_ALLOW_ORIGIN_REGEX") or None
    trusted_proxy_cidrs = tuple(
        ip_network(proxy_range.strip(), strict=False)
        for proxy_range in os.getenv("TRUSTED_PROXY_CIDRS", "").split(",")
        if proxy_range.strip()
    )


settings = Settings()
