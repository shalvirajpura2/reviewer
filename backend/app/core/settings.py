import os


class Settings:
    github_token = os.getenv("GITHUB_TOKEN")
    github_api_base = os.getenv("GITHUB_API_BASE", "https://api.github.com")
    backend_port = int(os.getenv("BACKEND_PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    stale_cache_ttl_seconds = int(os.getenv("STALE_CACHE_TTL_SECONDS", "43200"))
    analyze_window_seconds = int(os.getenv("ANALYZE_WINDOW_SECONDS", "60"))
    analyze_requests_per_window = int(os.getenv("ANALYZE_REQUESTS_PER_WINDOW", "6"))
    preview_window_seconds = int(os.getenv("PREVIEW_WINDOW_SECONDS", "60"))
    preview_requests_per_window = int(os.getenv("PREVIEW_REQUESTS_PER_WINDOW", "12"))
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
    cors_allow_origin_regex = os.getenv("CORS_ALLOW_ORIGIN_REGEX", r"https://.*\.vercel\.app") or None


settings = Settings()
