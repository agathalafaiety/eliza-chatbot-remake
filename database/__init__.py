"""Persistência SQLite; o mecanismo Classic permanece independente deste pacote."""

from database.repository import (
    ConversationConflictError,
    ConversationNotFoundError,
    ConversationRepository,
    SavedConversation,
    SavedTurn,
    StorageError,
    StoredConversation,
    StoredMessage,
)

__all__ = [
    "ConversationConflictError",
    "ConversationNotFoundError",
    "ConversationRepository",
    "SavedConversation",
    "SavedTurn",
    "StorageError",
    "StoredConversation",
    "StoredMessage",
]
