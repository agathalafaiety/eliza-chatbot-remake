"""Ciclo de vida real em arquivo, integridade, transações e concorrência SQLite."""

from __future__ import annotations

import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import event, insert
from sqlalchemy.exc import IntegrityError

from database import (
    ConversationConflictError,
    ConversationNotFoundError,
    ConversationRepository,
    StorageError,
)
from database.models import Message


@pytest.fixture
def repository(tmp_path: Path):
    with ConversationRepository(tmp_path / "conversas.sqlite3") as repository:
        yield repository


def test_create_empty_conversation(repository: ConversationRepository) -> None:
    row = repository.create_conversation("  Meu futuro  ")
    assert row.title == "Meu futuro"
    assert row.mode == "classic"
    assert row.language == "pt-BR"
    assert row.revision == 0
    assert row.created_at == row.updated_at
    assert row.created_at.tzinfo == UTC
    assert repository.get_history(row.id).messages == ()
    with pytest.raises(FrozenInstanceError):
        row.title = "Outra conversa"  # type: ignore[misc]


def test_file_survives_close_and_reopen_with_unicode_and_order(tmp_path: Path) -> None:
    path = tmp_path / "pasta com espaço" / "memória.sqlite3"
    with ConversationRepository(path) as repository:
        row = repository.create_conversation("Minha mãe e meu futuro")
        turn = repository.append_turn(
            row.id, "Olá, mãe! 🌻", "Como você se sente?", rule_id="family", expected_revision=0
        )
        repository.append_turn(row.id, "Outra mensagem", "Outra resposta", expected_revision=1)
    assert path.is_file()
    with ConversationRepository(path) as reopened:
        saved = reopened.get_history(row.id)
        assert saved.conversation.revision == 2
        assert [message.position for message in saved.messages] == [0, 1, 2, 3]
        assert [message.role for message in saved.messages] == ["user", "assistant"] * 2
        assert saved.messages[0].content == "Olá, mãe! 🌻"
        assert saved.messages[1].rule_id == "family"
        assert saved.messages[0].id == turn.user.id
        assert len({message.id for message in saved.messages}) == 4
        assert saved.conversation.created_at == row.created_at
        assert saved.conversation.updated_at >= row.updated_at
        assert all(message.created_at.tzinfo == UTC for message in saved.messages)


def test_list_most_recent_first_and_paginate(
    repository: ConversationRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    # O relógio do Windows pode devolver a mesma data para operações consecutivas.
    # Datas controladas testam a ordenação sem depender da resolução do relógio.
    start = datetime(2026, 1, 1, tzinfo=UTC)
    times = iter(start + timedelta(seconds=index) for index in range(3))

    class Clock:
        @staticmethod
        def now(timezone):
            return next(times)

    monkeypatch.setattr("database.repository.datetime", Clock)
    first = repository.create_conversation("Primeira")
    second = repository.create_conversation("Segunda")
    assert repository.list_conversations()[0].id == second.id
    repository.append_turn(first.id, "Oi", "Olá", expected_revision=0)
    assert repository.list_conversations(limit=1)[0].id == first.id
    assert repository.list_conversations(limit=1, offset=1)[0].id == second.id
    assert repository.list_conversations(offset=20) == ()


def test_delete_cascades_without_affecting_other_conversations(tmp_path: Path) -> None:
    path = tmp_path / "delete.sqlite3"
    with ConversationRepository(path) as repository:
        deleted = repository.create_conversation("Excluir esta")
        kept = repository.create_conversation("Preservar esta")
        repository.append_turn(deleted.id, "Oi", "Olá", expected_revision=0)
        repository.append_turn(kept.id, "Bom dia", "Olá novamente", expected_revision=0)
        assert repository.delete_conversation(deleted.id)
        assert not repository.delete_conversation(deleted.id)
        assert repository.get_conversation(deleted.id) is None
        assert len(repository.get_history(kept.id).messages) == 2
    with sqlite3.connect(path) as connection:
        count = connection.execute(
            "SELECT count(*) FROM messages WHERE conversation_id = ?", (deleted.id,)
        ).fetchone()[0]
        assert count == 0
    with ConversationRepository(path) as reopened:
        assert reopened.get_conversation(deleted.id) is None
        assert [row.id for row in reopened.list_conversations()] == [kept.id]


def test_missing_conversation(repository: ConversationRepository) -> None:
    assert repository.get_conversation("inexistente") is None
    with pytest.raises(ConversationNotFoundError):
        repository.get_history("inexistente")
    with pytest.raises(ConversationNotFoundError):
        repository.append_turn("inexistente", "Oi", "Olá", expected_revision=0)
    assert not repository.delete_conversation("inexistente")


def test_stale_revision_does_not_overwrite_or_append(repository: ConversationRepository) -> None:
    row = repository.create_conversation()
    repository.append_turn(row.id, "primeira", "resposta", expected_revision=0)
    before = repository.get_history(row.id)
    with pytest.raises(ConversationConflictError):
        repository.append_turn(row.id, "segunda", "resposta perdida", expected_revision=0)
    assert repository.get_history(row.id) == before


def test_partial_insert_failure_rolls_back_pair_revision_and_timestamp(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "atomic.sqlite3"
    with ConversationRepository(path) as repository:
        row = repository.create_conversation()
        before = repository.get_history(row.id)
        with sqlite3.connect(path) as connection:
            connection.execute(
                "CREATE TRIGGER reject_assistant BEFORE INSERT ON messages "
                "WHEN NEW.role = 'assistant' BEGIN SELECT RAISE(ABORT, 'segredo-do-trigger'); END"
            )
        with caplog.at_level(logging.ERROR), pytest.raises(StorageError) as error:
            repository.append_turn(
                row.id, "mensagem-privada", "resposta-privada", expected_revision=0
            )
        assert repository.get_history(row.id) == before
        for secret in ("mensagem-privada", "resposta-privada", "segredo-do-trigger"):
            assert secret not in str(error.value)
            assert secret not in caplog.text
        with sqlite3.connect(path) as connection:
            connection.execute("DROP TRIGGER reject_assistant")
        assert repository.append_turn(row.id, "nova", "resposta", expected_revision=0)


def test_foreign_keys_reject_orphan_messages(repository: ConversationRepository) -> None:
    with pytest.raises(IntegrityError), repository._engine.begin() as connection:
        connection.execute(
            insert(Message).values(
                id="orphan",
                conversation_id="missing",
                position=0,
                role="user",
                content="Mensagem sem conversa",
                created_at=datetime.now(UTC),
            )
        )


def test_concurrent_writers_cannot_save_same_revision(tmp_path: Path) -> None:
    path = tmp_path / "concurrent.sqlite3"
    with ConversationRepository(path) as first, ConversationRepository(path) as second:
        row = first.create_conversation()
        barrier = Barrier(2)

        def send(repository: ConversationRepository, text: str) -> str:
            barrier.wait(timeout=5)
            try:
                repository.append_turn(row.id, text, "Resposta", expected_revision=0)
            except ConversationConflictError:
                return "conflict"
            return "saved"

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(send, first, "Primeira"),
                executor.submit(send, second, "Segunda"),
            ]
            assert sorted(future.result(timeout=10) for future in futures) == ["conflict", "saved"]
        saved = first.get_history(row.id)
        assert saved.conversation.revision == 1
        assert len(saved.messages) == 2


def test_history_is_a_consistent_snapshot_during_a_concurrent_write(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.db"
    with ConversationRepository(path) as reader, ConversationRepository(path) as writer:
        row = reader.create_conversation()
        wrote = False

        def write_between_reads(connection, cursor, statement, parameters, context, executemany):
            nonlocal wrote
            if "FROM messages" in statement and not wrote:
                wrote = True
                writer.append_turn(row.id, "oi", "olá", expected_revision=0)

        event.listen(reader._engine, "before_cursor_execute", write_between_reads)
        saved = reader.get_history(row.id)
        assert wrote
        assert saved.conversation.revision == 0
        assert saved.messages == ()
        assert reader.get_history(row.id).conversation.revision == 1
        assert len(reader.get_history(row.id).messages) == 2


def test_sql_like_input_is_stored_as_text(repository: ConversationRepository) -> None:
    payload = "'); DROP TABLE conversations; --"
    row = repository.create_conversation(payload)
    repository.append_turn(row.id, payload, "Resposta", expected_revision=0)
    assert repository.get_history(row.id).messages[0].content == payload
    assert repository.get_conversation(payload) is None
    assert repository.get_conversation(row.id).title == payload


def test_ai_mode_is_only_reserved_metadata(repository: ConversationRepository) -> None:
    row = repository.create_conversation(mode="ai")
    assert repository.get_conversation(row.id).mode == "ai"


@pytest.mark.parametrize("title", ["", "  ", "x" * 121])
def test_invalid_title_is_rejected(repository: ConversationRepository, title: str) -> None:
    with pytest.raises(ValueError):
        repository.create_conversation(title)
    assert repository.list_conversations() == ()


def test_invalid_mode_is_rejected(repository: ConversationRepository) -> None:
    with pytest.raises(ValueError):
        repository.create_conversation(mode="unknown")  # type: ignore[arg-type]


@pytest.mark.parametrize(("user", "assistant"), [(" ", "resposta"), ("oi", "\n"), ("", "")])
def test_invalid_messages_cannot_leave_partial_turn(
    repository: ConversationRepository, user: str, assistant: str
) -> None:
    row = repository.create_conversation()
    with pytest.raises(ValueError):
        repository.append_turn(row.id, user, assistant, expected_revision=0)
    assert repository.get_history(row.id).conversation.revision == 0
    assert repository.get_history(row.id).messages == ()


@pytest.mark.parametrize("revision", [-1, True, "0"])
def test_invalid_revision(repository: ConversationRepository, revision: object) -> None:
    row = repository.create_conversation()
    with pytest.raises((ValueError, TypeError)):
        repository.append_turn(row.id, "oi", "olá", expected_revision=revision)


@pytest.mark.parametrize(("limit", "offset"), [(0, 0), (1001, 0), (1, -1), (True, 0), (1, "0")])
def test_invalid_pagination(
    repository: ConversationRepository, limit: object, offset: object
) -> None:
    with pytest.raises((ValueError, TypeError)):
        repository.list_conversations(limit=limit, offset=offset)


def test_closed_repository_is_explicit(tmp_path: Path) -> None:
    repository = ConversationRepository(tmp_path / "closed.db")
    repository.close()
    repository.close()
    with pytest.raises(StorageError, match="fechado"):
        repository.list_conversations()


def test_memory_database_works_across_repository_operations() -> None:
    with ConversationRepository(":memory:") as repository:
        row = repository.create_conversation()
        repository.append_turn(row.id, "oi", "olá", expected_revision=0)
        assert len(repository.get_history(row.id).messages) == 2


def test_cannot_open_database_returns_sanitized_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "secret-parent"
    path.write_text("impede a criação de diretório", encoding="utf-8")
    with caplog.at_level(logging.ERROR), pytest.raises(StorageError) as error:
        ConversationRepository(path / "database.db")
    assert "secret-parent" not in str(error.value)
    assert "secret-parent" not in caplog.text
