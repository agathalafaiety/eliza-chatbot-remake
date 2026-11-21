"""Retomada Classic mantém o comportamento e nunca regrava turnos anteriores."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from database import ConversationConflictError, ConversationNotFoundError, ConversationRepository
from eliza import ClassicEliza
from eliza.memory import ConversationMemory, HistoryMismatchError


def test_resume_after_reopen_matches_uninterrupted_session(tmp_path: Path) -> None:
    path = tmp_path / "resume.db"
    uninterrupted = ClassicEliza()
    messages = [
        "Estou preocupado com meu futuro.",
        "Estou preocupado com meu trabalho.",
        "Tenho medo de fracassar.",
        "Tenho medo de fracassar.",
        "hmm",
        "talvez",
    ]
    with ConversationRepository(path) as repository:
        conversation = repository.create_conversation("Retomar")
        memory = ConversationMemory(repository)
        for message in messages[:3]:
            saved = memory.send(conversation.id, message)
            assert saved.assistant.content == uninterrupted.respond(message)
    with ConversationRepository(path) as reopened:
        memory = ConversationMemory(reopened)
        for message in messages[3:]:
            saved = memory.send(conversation.id, message)
            assert saved.assistant.content == uninterrupted.respond(message)
        assert len(reopened.get_history(conversation.id).messages) == len(messages) * 2
        assert memory.restore_classic(conversation.id).history == uninterrupted.history


def test_resume_uses_full_history_even_beyond_session_window(tmp_path: Path) -> None:
    with ConversationRepository(tmp_path / "long.db") as repository:
        row = repository.create_conversation()
        memory = ConversationMemory(repository)
        uninterrupted = ClassicEliza()
        for index in range(25):
            message = f"Estou preocupado com meu projeto {index}."
            assert memory.send(row.id, message).assistant.content == uninterrupted.respond(message)
        assert len(repository.get_history(row.id).messages) == 50
        assert len(memory.restore_classic(row.id).history) == 20
        assert memory.send(row.id, "hmm").assistant.content == uninterrupted.respond("hmm")


def test_empty_conversation_can_be_restored(tmp_path: Path) -> None:
    with ConversationRepository(tmp_path / "empty.db") as repository:
        row = repository.create_conversation()
        assert ConversationMemory(repository).restore_classic(row.id).history == ()


def test_invalid_input_does_not_advance_history(tmp_path: Path) -> None:
    with ConversationRepository(tmp_path / "invalid.db") as repository:
        row = repository.create_conversation()
        memory = ConversationMemory(repository)
        before = repository.get_history(row.id)
        for message in ("", "x" * 4001):
            with pytest.raises(ValueError):
                memory.send(row.id, message)
            assert repository.get_history(row.id) == before


def test_conflict_does_not_advance_rebuilt_session(tmp_path: Path, monkeypatch) -> None:
    with ConversationRepository(tmp_path / "conflict.db") as repository:
        row = repository.create_conversation()
        memory = ConversationMemory(repository)
        original = repository.append_turn

        def fail(*args, **kwargs):
            raise ConversationConflictError("Conflito simulado")

        monkeypatch.setattr(repository, "append_turn", fail)
        with pytest.raises(ConversationConflictError):
            memory.send(row.id, "Estou preocupado com meu futuro.")
        assert repository.get_history(row.id).messages == ()
        monkeypatch.setattr(repository, "append_turn", original)
        result = memory.send(row.id, "Estou preocupado com meu futuro.")
        assert result.assistant.content == ClassicEliza().respond(
            "Estou preocupado com meu futuro."
        )


def test_missing_and_deleted_conversation_cannot_receive_messages(tmp_path: Path) -> None:
    with ConversationRepository(tmp_path / "deleted.db") as repository:
        row = repository.create_conversation()
        repository.delete_conversation(row.id)
        with pytest.raises(ConversationNotFoundError):
            ConversationMemory(repository).send(row.id, "oi")


def test_modes_are_not_silently_changed(tmp_path: Path) -> None:
    with ConversationRepository(tmp_path / "mode.db") as repository:
        row = repository.create_conversation(mode="ai")
        with pytest.raises(ValueError, match="Classic"):
            ConversationMemory(repository).send(row.id, "oi")
        assert repository.get_history(row.id).messages == ()


def test_mismatched_response_is_preserved_but_cannot_be_replayed(tmp_path: Path) -> None:
    with ConversationRepository(tmp_path / "mismatch.db") as repository:
        row = repository.create_conversation()
        repository.append_turn(row.id, "oi", "Resposta de outra versão", expected_revision=0)
        before = repository.get_history(row.id)
        with pytest.raises(HistoryMismatchError, match="regras atuais"):
            ConversationMemory(repository).send(row.id, "sim")
        assert repository.get_history(row.id) == before


def test_incomplete_history_is_not_extended(tmp_path: Path) -> None:
    path = tmp_path / "incomplete.db"
    with ConversationRepository(path) as repository:
        row = repository.create_conversation()
        memory = ConversationMemory(repository)
        memory.send(row.id, "oi")
        with sqlite3.connect(path) as connection:
            connection.execute("DELETE FROM messages WHERE role = 'assistant'")
        with pytest.raises(HistoryMismatchError, match="incompleto"):
            memory.send(row.id, "sim")
        assert len(repository.get_history(row.id).messages) == 1


@pytest.mark.parametrize(("column", "value"), [("role", "user"), ("rule_id", "outra_regra")])
def test_modified_role_or_rule_does_not_silently_change_the_session(
    tmp_path: Path, column: str, value: str
) -> None:
    path = tmp_path / "modified.db"
    with ConversationRepository(path) as repository:
        row = repository.create_conversation()
        memory = ConversationMemory(repository)
        memory.send(row.id, "oi")
        with sqlite3.connect(path) as connection:
            # column é um dos dois valores fixos da parametrização acima.
            connection.execute(f"UPDATE messages SET {column} = ? WHERE position = 1", (value,))
        before = repository.get_history(row.id)
        with pytest.raises(HistoryMismatchError):
            memory.send(row.id, "sim")
        assert repository.get_history(row.id) == before


def test_two_conversations_have_independent_context(tmp_path: Path) -> None:
    with ConversationRepository(tmp_path / "isolation.db") as repository:
        first, second = repository.create_conversation(), repository.create_conversation()
        memory = ConversationMemory(repository)
        memory.send(first.id, "Tenho medo de fracassar.")
        assert memory.send(second.id, "hmm").assistant.rule_id == "fallback"
        assert memory.send(first.id, "hmm").assistant.rule_id == "memory"
