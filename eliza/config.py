"""Configuração local de persistência, sem alterar variáveis globais do processo."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, SecretStr, field_validator
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = Path("data") / "eliza.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    database_url: str = DEFAULT_DATABASE_URL
    gemini_api_key: SecretStr | None = None
    gemini_model: str = DEFAULT_GEMINI_MODEL

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        try:
            url = make_url(value)
        except ArgumentError:
            raise ValueError(f"Use uma URL SQLite válida como {DEFAULT_DATABASE_URL}.") from None
        if (
            url.drivername != "sqlite"
            or not url.database
            or url.host is not None
            or url.username is not None
            or url.password is not None
            or url.query
        ):
            raise ValueError("Use uma URL local SQLite sem credenciais ou parâmetros.")
        return value

    def database_path(self, base_dir: Path = PROJECT_ROOT) -> Path | str:
        database = make_url(self.database_url).database
        if database == ":memory:":
            return ":memory:"
        assert database is not None  # Validado acima.
        return (base_dir / database).resolve()


def load_settings(env_file: Path | None = None) -> Settings:
    """Lê a configuração local, dando prioridade às variáveis do ambiente."""
    values = dotenv_values(env_file if env_file is not None else PROJECT_ROOT / ".env")
    database_url = os.environ.get("ELIZA_DATABASE_URL", values.get("ELIZA_DATABASE_URL"))
    api_key = (os.environ.get("GEMINI_API_KEY", values.get("GEMINI_API_KEY")) or "").strip()
    if not api_key:
        api_key = (os.environ.get("GOOGLE_API_KEY", values.get("GOOGLE_API_KEY")) or "").strip()
    model = (os.environ.get("GEMINI_MODEL", values.get("GEMINI_MODEL")) or "").strip()
    return Settings(
        database_url=DEFAULT_DATABASE_URL if database_url is None else database_url,
        gemini_api_key=SecretStr(api_key) if api_key else None,
        gemini_model=model or DEFAULT_GEMINI_MODEL,
    )
