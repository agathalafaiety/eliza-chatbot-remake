"""Índice Chroma local e reconstruível. O conteúdo das mensagens vem do SQLite."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from database import ConversationRepository, SavedConversation, StorageError, StoredMessage

if TYPE_CHECKING:
    from chromadb.api import ClientAPI

EMBEDDING_MODEL = "gemini-embedding-001"
MAX_INDEX_TURNS = 100
MAX_EMBED_BATCH = 12
MAX_RECALLED_TURNS = 3
MAX_RECALLED_CHARS = 3600
MAX_COSINE_DISTANCE = 0.55

logger = logging.getLogger(__name__)
index_lock = Lock()


def _client(path: Path) -> ClientAPI:
    from chromadb import PersistentClient, Settings

    return PersistentClient(path=str(path.resolve()), settings=Settings(anonymized_telemetry=False))


def _collection_name(conversation_id: str) -> str:
    # A versão identifica a combinação de modelo, dimensões e formato dos turnos.
    return f"eliza-mem-v1-{conversation_id}"


def recall(
    repository: ConversationRepository,
    path: Path,
    saved: SavedConversation,
    recent: tuple[StoredMessage, ...],
    message: str,
    embed: Callable[[list[str], bool], list[list[float]]],
) -> tuple[StoredMessage, ...]:
    """Busca turnos antigos da mesma conversa, removendo os que já estão no contexto recente."""
    cutoff = len(saved.messages) - len(recent)
    start = max(0, cutoff - 2 * MAX_INDEX_TURNS)
    turns = {
        user.id: (user, answer)
        for user, answer in zip(
            saved.messages[start:cutoff:2], saved.messages[start + 1 : cutoff : 2], strict=True
        )
        if len(user.content) + len(answer.content) <= MAX_RECALLED_CHARS
    }
    if not turns:
        return ()

    try:
        with index_lock:
            if repository.get_conversation(saved.conversation.id) is None:
                return ()
            collection = _client(path).get_or_create_collection(
                name=_collection_name(saved.conversation.id),
                embedding_function=None,
                configuration={"hnsw": {"space": "cosine"}},
            )
            indexed = set(collection.get(include=[])["ids"])
            obsolete = indexed - turns.keys()
            if obsolete:
                collection.delete(ids=sorted(obsolete))
            missing = [item for item in reversed(turns) if item not in indexed][:MAX_EMBED_BATCH]
            if missing:
                documents = [
                    f"Você: {turns[item][0].content}\nELIZA: {turns[item][1].content}"
                    for item in missing
                ]
                collection.upsert(ids=missing, embeddings=embed(documents, False))
                indexed.update(missing)

            matches = collection.query(
                query_embeddings=embed([message], True),
                ids=sorted(indexed & turns.keys()),
                n_results=MAX_RECALLED_TURNS,
                include=["distances"],
            )
            selected: list[tuple[StoredMessage, StoredMessage]] = []
            remaining = MAX_RECALLED_CHARS
            for item, distance in zip(
                matches["ids"][0], (matches["distances"] or [[]])[0], strict=True
            ):
                user, answer = turns[item]
                size = len(user.content) + len(answer.content)
                if distance <= MAX_COSINE_DISTANCE and size <= remaining:
                    selected.append((user, answer))
                    remaining -= size
            return tuple(
                message
                for pair in sorted(selected, key=lambda t: t[0].position)
                for message in pair
            )
    except Exception as error:
        # O índice e a API de embeddings são opcionais. Preserve o chat com os turnos recentes.
        logger.warning("Memória semântica indisponível (%s).", type(error).__name__)
        return ()


def delete_conversation(
    repository: ConversationRepository, path: Path, conversation_id: str
) -> bool:
    """Remove os vetores antes do histórico para permitir repetir uma exclusão interrompida."""
    conversation = repository.get_conversation(conversation_id)
    if conversation is None:
        return False
    if conversation.mode != "ai":
        return repository.delete_conversation(conversation_id)

    with index_lock:
        if (path / "chroma.sqlite3").is_file():
            try:
                from chromadb.errors import NotFoundError

                try:
                    _client(path).delete_collection(_collection_name(conversation_id))
                except NotFoundError:
                    pass
            except Exception as error:
                logger.warning("Falha ao excluir o índice da conversa (%s).", type(error).__name__)
                raise StorageError(
                    "Não foi possível excluir o índice ChromaDB. "
                    "Confira se o ChromaDB está instalado e tente novamente."
                ) from None
        return repository.delete_conversation(conversation_id)
