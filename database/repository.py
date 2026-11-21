"""Operações transacionais sobre conversas e mensagens no SQLite."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from sqlalchemy import URL, Connection, create_engine, delete, event, select, update
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import Base, Conversation, Message
from eliza.config import DEFAULT_DATABASE_PATH, PROJECT_ROOT, Settings, load_settings

logger = logging.getLogger(__name__)
Mode = Literal["classic", "ai"]


class StorageError(RuntimeError):
    """Falha sanitizada de armazenamento."""


class ConversationNotFoundError(StorageError):
    """Conversa não existe ou foi excluída."""


class ConversationConflictError(StorageError):
    """A conversa mudou durante a interação; recarregar antes de repetir."""


@dataclass(frozen=True)
class StoredConversation:
    id: str
    title: str
    mode: str
    language: str
    revision: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class StoredMessage:
    id: str
    conversation_id: str
    position: int
    role: str
    content: str
    rule_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class SavedConversation:
    conversation: StoredConversation
    messages: tuple[StoredMessage, ...]


@dataclass(frozen=True)
class SavedTurn:
    conversation: StoredConversation
    user: StoredMessage
    assistant: StoredMessage


def _conversation_record(row: Conversation) -> StoredConversation:
    return StoredConversation(
        row.id, row.title, row.mode, row.language, row.revision, row.created_at, row.updated_at
    )


def _message_record(row: Message) -> StoredMessage:
    return StoredMessage(
        row.id,
        row.conversation_id,
        row.position,
        row.role,
        row.content,
        row.rule_id,
        row.created_at,
    )


def _nonempty(value: str, label: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{label} deve ser uma string.")
    if not value.strip():
        raise ValueError(f"{label} não pode ficar vazio.")


def _configure_connection(connection: sqlite3.Connection, record: object) -> None:
    # Controle explícito de BEGIN funciona também no Python 3.11. SELECT passa a
    # participar da transação, mantendo metadados e mensagens no mesmo snapshot.
    connection.isolation_level = None
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def _begin_transaction(connection: Connection) -> None:
    connection.exec_driver_sql("BEGIN")


class ConversationRepository:
    """Gerencia o arquivo SQLite e devolve registros independentes da sessão ORM."""

    def __init__(self, database_path: Path | str = PROJECT_ROOT / DEFAULT_DATABASE_PATH) -> None:
        self._closed = False
        in_memory = str(database_path) == ":memory:"
        self._engine = None
        try:
            path = ":memory:" if in_memory else str(Path(database_path).resolve())
            if not in_memory:
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            options = {"poolclass": StaticPool} if in_memory else {}
            self._engine = create_engine(
                URL.create("sqlite", database=path),
                connect_args={"check_same_thread": False, "timeout": 5},
                hide_parameters=True,
                **options,
            )
            event.listen(self._engine, "connect", _configure_connection)
            if not in_memory:
                # Antes do listener BEGIN: journal_mode deve mudar fora da transação.
                with self._engine.connect() as connection:
                    connection.exec_driver_sql("PRAGMA journal_mode=WAL")
                    connection.commit()
            event.listen(self._engine, "begin", _begin_transaction)
            Base.metadata.create_all(self._engine)
            self._sessions = sessionmaker(self._engine, expire_on_commit=False)
        except (OSError, SQLAlchemyError) as error:
            if self._engine is not None:
                self._engine.dispose()
            logger.error("Falha ao abrir armazenamento (%s).", type(error).__name__)
            raise StorageError("Não foi possível abrir o banco de conversas.") from None

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> ConversationRepository:
        """Abre o banco indicado pela configuração explícita ou pelo ambiente local."""
        configuration = settings if settings is not None else load_settings()
        return cls(configuration.database_path())

    def __enter__(self) -> ConversationRepository:
        self._ensure_open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise StorageError("O repositório foi fechado. Abra uma nova instância.")

    @contextmanager
    def _transaction(self) -> Iterator[Session]:
        self._ensure_open()
        try:
            with self._sessions.begin() as session:
                yield session
        except OperationalError as error:
            logger.error("Falha transacional de armazenamento (%s).", type(error).__name__)
            if getattr(error.orig, "sqlite_errorcode", None) in (
                sqlite3.SQLITE_BUSY,
                sqlite3.SQLITE_BUSY_SNAPSHOT,
            ):
                raise ConversationConflictError(
                    "O banco está ocupado. Recarregue a conversa antes de tentar novamente."
                ) from None
            raise StorageError("Não foi possível acessar o histórico de conversas.") from None
        except SQLAlchemyError as error:
            logger.error("Falha transacional de armazenamento (%s).", type(error).__name__)
            raise StorageError("Não foi possível salvar ou recuperar a conversa.") from None

    def create_conversation(
        self, title: str = "Nova conversa", *, mode: Mode = "classic"
    ) -> StoredConversation:
        _nonempty(title, "O título")
        if len(title.strip()) > 120:
            raise ValueError("O título deve ter no máximo 120 caracteres.")
        if mode not in ("classic", "ai"):
            raise ValueError("O modo deve ser 'classic' ou 'ai'.")
        now = datetime.now(UTC)
        with self._transaction() as session:
            row = Conversation(
                id=str(uuid4()),
                title=title.strip(),
                mode=mode,
                language="pt-BR",
                revision=0,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            result = _conversation_record(row)
        return result

    def list_conversations(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[StoredConversation, ...]:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (limit, offset)):
            raise TypeError("Limite e deslocamento devem ser inteiros.")
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("Use limite entre 1 e 1000 e deslocamento não negativo.")
        with self._transaction() as session:
            rows = session.scalars(
                select(Conversation)
                .order_by(Conversation.updated_at.desc(), Conversation.id)
                .offset(offset)
                .limit(limit)
            )
            return tuple(_conversation_record(row) for row in rows)

    def get_conversation(self, conversation_id: str) -> StoredConversation | None:
        _nonempty(conversation_id, "O identificador")
        with self._transaction() as session:
            row = session.get(Conversation, conversation_id)
            return None if row is None else _conversation_record(row)

    def get_history(self, conversation_id: str) -> SavedConversation:
        _nonempty(conversation_id, "O identificador")
        with self._transaction() as session:
            row = session.get(Conversation, conversation_id)
            if row is None:
                raise ConversationNotFoundError("A conversa não existe ou foi excluída.")
            messages = session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.position)
            )
            return SavedConversation(
                _conversation_record(row), tuple(_message_record(message) for message in messages)
            )

    def append_turn(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        *,
        rule_id: str | None = None,
        expected_revision: int,
    ) -> SavedTurn:
        """Salva o par integralmente ou não salva nada. Revisão protege contra concorrência."""
        for value, label in (
            (conversation_id, "O identificador"),
            (user_message, "A mensagem"),
            (assistant_message, "A resposta"),
        ):
            _nonempty(value, label)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise TypeError("A revisão deve ser um inteiro.")
        if expected_revision < 0:
            raise ValueError("A revisão não pode ser negativa.")
        if rule_id is not None:
            _nonempty(rule_id, "A regra")
            if len(rule_id) > 50:
                raise ValueError("O identificador da regra deve ter até 50 caracteres.")
        now = datetime.now(UTC)
        with self._transaction() as session:
            row = session.scalars(
                update(Conversation)
                .where(
                    Conversation.id == conversation_id, Conversation.revision == expected_revision
                )
                .values(revision=expected_revision + 1, updated_at=now)
                .returning(Conversation)
            ).one_or_none()
            if row is None:
                if session.get(Conversation, conversation_id) is None:
                    raise ConversationNotFoundError("A conversa não existe ou foi excluída.")
                raise ConversationConflictError(
                    "A conversa mudou. Recarregue antes de tentar novamente."
                )
            user = Message(
                id=str(uuid4()),
                conversation_id=conversation_id,
                position=expected_revision * 2,
                role="user",
                content=user_message,
                rule_id=None,
                created_at=now,
            )
            assistant = Message(
                id=str(uuid4()),
                conversation_id=conversation_id,
                position=expected_revision * 2 + 1,
                role="assistant",
                content=assistant_message,
                rule_id=rule_id,
                created_at=now,
            )
            session.add_all((user, assistant))
            session.flush()
            result = SavedTurn(
                _conversation_record(row), _message_record(user), _message_record(assistant)
            )
        return result

    def delete_conversation(self, conversation_id: str) -> bool:
        """Exclui uma conversa e suas mensagens por FK; ausentes retornam False."""
        _nonempty(conversation_id, "O identificador")
        with self._transaction() as session:
            removed = session.execute(
                delete(Conversation)
                .where(Conversation.id == conversation_id)
                .returning(Conversation.id)
            ).scalar_one_or_none()
            return removed is not None
