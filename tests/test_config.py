"""Configuração de banco previsível entre o terminal e o notebook."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import URL

from database import ConversationRepository
from eliza.config import Settings, load_settings


def test_relative_database_path_is_anchored_to_base_directory(tmp_path: Path) -> None:
    assert Settings().database_path(tmp_path) == tmp_path / "data" / "eliza.db"


def test_settings_default_without_environment_or_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ELIZA_DATABASE_URL", raising=False)
    assert load_settings(tmp_path / "missing.env").database_url == "sqlite:///data/eliza.db"


def test_dotenv_and_environment_precedence_without_global_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / ".env"
    path.write_text("ELIZA_DATABASE_URL=sqlite:///arquivo.db\n", encoding="utf-8")
    monkeypatch.delenv("ELIZA_DATABASE_URL", raising=False)
    assert load_settings(path).database_url == "sqlite:///arquivo.db"
    assert "ELIZA_DATABASE_URL" not in os.environ
    monkeypatch.setenv("ELIZA_DATABASE_URL", "sqlite:///ambiente.db")
    assert load_settings(path).database_url == "sqlite:///ambiente.db"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "postgresql://host/db",
        "sqlite://",
        "not-a-url",
        "sqlite:///dados.db?mode=ro",
        "sqlite://user:secret@host/db",
    ],
)
def test_invalid_urls_are_rejected_without_disclosing_input(value: str) -> None:
    with pytest.raises(ValidationError) as error:
        Settings(database_url=value)
    assert "user:secret" not in str(error.value)


def test_absolute_path_and_factory(tmp_path: Path) -> None:
    path = tmp_path / "configurado.db"
    settings = Settings(database_url=URL.create("sqlite", database=str(path)).render_as_string())
    assert settings.database_path() == path
    with ConversationRepository.from_settings(settings) as repository:
        assert repository.create_conversation().language == "pt-BR"
    assert path.is_file()


def test_memory_setting() -> None:
    assert Settings(database_url="sqlite:///:memory:").database_path() == ":memory:"
