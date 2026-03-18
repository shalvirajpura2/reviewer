import os


class Settings:
    github_token = os.getenv("GITHUB_TOKEN")
    github_api_base = os.getenv("GITHUB_API_BASE", "https://api.github.com")
    backend_port = int(os.getenv("BACKEND_PORT", "8000"))
    cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    cors_allow_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOW_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]


settings = Settings()
