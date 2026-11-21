"""Busca semântica com Chroma local real e embeddings controlados."""

from pathlib import Path

import pytest
from pydantic import SecretStr

from database import ConversationRepository, StorageError
from eliza.ai import send_ai_turn
from eliza.config import Settings
from eliza.semantic_memory import _client, _collection_name, delete_conversation, recall

chroma = pytest.importorskip("chromadb")


def vector(text: str) -> list[float]:
    return [1.0, 0.0, 0.0] if "azul" in text else [0.0, 1.0, 0.0]


def embed(texts: list[str], query: bool) -> list[list[float]]:
    return [vector(text) for text in texts]


def test_recall_returns_only_older_turns_in_same_conversation_and_reuses_index(
    tmp_path: Path,
) -> None:
    path = tmp_path / "index"
    with ConversationRepository(tmp_path / "history.db") as repo:
        one = repo.create_conversation(mode="ai")
        two = repo.create_conversation(mode="ai")
        relevant = repo.append_turn(one.id, "Meu caderno é azul", "Conte mais", expected_revision=0)
        repo.append_turn(one.id, "Aprendi violão", "Como começou?", expected_revision=1)
        recent = repo.append_turn(one.id, "Outra coisa azul", "Sim?", expected_revision=2)
        repo.append_turn(two.id, "Outro caderno azul", "Segredo", expected_revision=0)
        second = repo.get_history(two.id)
        recall(repo, path, second, (), "azul", embed)

        first = repo.get_history(one.id)
        recent_messages = (recent.user, recent.assistant)
        assert recall(repo, path, first, recent_messages, "azul", embed) == (
            relevant.user,
            relevant.assistant,
        )
        ids = _client(path).get_collection(_collection_name(one.id)).get(include=["documents"])
        assert len(ids["ids"]) == 2
        assert not any(ids["documents"] or [])

        def query_only(texts: list[str], query: bool) -> list[list[float]]:
            assert query, "O índice persistente já tem os vetores dos documentos"
            return embed(texts, query)

        assert recall(repo, path, first, recent_messages, "azul", query_only) == (
            relevant.user,
            relevant.assistant,
        )


def test_ai_uses_recall_only_when_enabled_and_falls_back_when_embeddings_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "index"
    sent = []
    monkeypatch.setattr("eliza.ai._embed", lambda settings, texts, query: embed(texts, query))

    def generate(settings, history, message):
        sent.append(history)
        return "Resposta fictícia"

    monkeypatch.setattr("eliza.ai._generate", generate)
    with ConversationRepository(tmp_path / "history.db") as repo:
        item = repo.create_conversation(mode="ai")
        for revision in range(11):
            text = "caderno azul" if revision == 0 else f"assunto {revision}"
            repo.append_turn(item.id, text, "resposta anterior", expected_revision=revision)
        history = repo.get_history(item.id).messages
        settings = Settings(gemini_api_key=SecretStr("teste"), chroma_path=path)
        send_ai_turn(repo, settings, item.id, "azul")
        assert sent[-1] == history[-20:]
        assert not path.exists()

        enabled = settings.model_copy(update={"semantic_memory": True})
        send_ai_turn(repo, enabled, item.id, "azul")
        assert sent[-1][:2] == history[:2]

        def fail(*args):
            raise RuntimeError("conteúdo que não deve ser mostrado")

        monkeypatch.setattr("eliza.ai._embed", fail)
        before = repo.get_history(item.id)
        send_ai_turn(repo, enabled, item.id, "azul")
        assert sent[-1] == before.messages[-20:]
        assert repo.get_history(item.id).conversation.revision == before.conversation.revision + 1


def test_exclusion_removes_only_selected_collection_and_sqlite_history(tmp_path: Path) -> None:
    path = tmp_path / "index"
    with ConversationRepository(tmp_path / "history.db") as repo:
        a = repo.create_conversation(mode="ai")
        b = repo.create_conversation(mode="ai")
        for conversation in (a, b):
            repo.append_turn(conversation.id, "azul", "resposta", expected_revision=0)
            recall(repo, path, repo.get_history(conversation.id), (), "azul", embed)

        assert delete_conversation(repo, path, a.id)
        assert repo.get_conversation(a.id) is None
        assert len(repo.get_history(b.id).messages) == 2
        with pytest.raises(chroma.errors.NotFoundError):
            _client(path).get_collection(_collection_name(a.id))
        assert _client(path).get_collection(_collection_name(b.id)).count() == 1


def test_index_deletion_failure_keeps_sqlite_history(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "index"
    path.mkdir()
    (path / "chroma.sqlite3").touch()

    def offline(path):
        raise OSError("detalhe privado")

    monkeypatch.setattr("eliza.semantic_memory._client", offline)
    with ConversationRepository(tmp_path / "history.db") as repo:
        item = repo.create_conversation(mode="ai")
        with pytest.raises(StorageError, match="excluir o índice"):
            delete_conversation(repo, path, item.id)
        assert repo.get_conversation(item.id) is not None

        classic = repo.create_conversation()
        assert delete_conversation(repo, path, classic.id)
