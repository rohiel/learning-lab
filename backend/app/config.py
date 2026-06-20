"""Runtime configuration, loaded from environment / .env.

The Anthropic API key lives ONLY here (read from the environment) and is never
returned to clients or logged.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # `anthropic_model` would otherwise trip pydantic's protected "model_" namespace check
        protected_namespaces=(),
    )

    # ---- Anthropic ----
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_timeout: float = 60.0
    anthropic_max_retries: int = 2
    # Question-generation calls are large and reasoning-heavy (10-15 questions),
    # so they get much more headroom than the quick grading/help calls.
    generation_timeout: float = 180.0
    generation_retries: int = 3

    # ---- Auth ----
    api_shared_secret: str = "change-me"

    # ---- Database ----
    database_url: str = "sqlite:///./data/tutor.db"

    # ---- Scheduler (Phase 2) ----
    scheduler_enabled: bool = True
    scheduler_tz: str = "America/New_York"
    scheduler_hour: int = 20

    # ---- CORS ----
    frontend_origin: str = "*"

    # ---- Question-pool sizing ----
    per_level_min: int = 5
    per_level_max: int = 7

    # ---- Static SPA serving (single-container deploy) ----
    static_dir: str = ""          # path to the built frontend; empty = API only (dev)
    spa_api_base: str = "/api"    # injected into the SPA at runtime

    # ---- First-run convenience ----
    auto_seed_student: bool = True
    default_student_name: str = "Anam"

    @property
    def cors_origins(self) -> list[str]:
        if self.frontend_origin.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]


settings = Settings()
