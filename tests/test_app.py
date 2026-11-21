"""Fluxos Streamlit com o Classic e um arquivo SQLite real por teste."""

from pathlib import Path

import pytest
from sqlalchemy import URL
from streamlit.testing.v1 import AppTest

from database import ConversationRepository
from eliza.config import PROJECT_ROOT


@pytest.fixture
def database_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "interface.sqlite3"
    monkeypatch.setenv(
        "ELIZA_DATABASE_URL", URL.create("sqlite", database=str(path)).render_as_string()
    )
    return path


def open_app() -> AppTest:
    app = AppTest.from_file(str(PROJECT_ROOT / "app.py")).run()
    assert not app.exception
    return app


def button(app: AppTest, label: str):
    return next(widget for widget in app.button if widget.label == label)


def test_create_send_and_resume_in_new_session(database_path: Path) -> None:
    app = open_app()
    assert not app.chat_input
    app.text_input[0].set_value("Meu futuro")
    button(app, "Nova conversa").click().run()
    assert not app.exception
    conversation_id = app.session_state["conversation_id"]

    app.chat_input[0].set_value("Estou preocupado com meu futuro.").run()
    assert not app.exception
    assert app.chat_message[1].text[0].value == "O que preocupa você em relação a seu futuro?"
    with ConversationRepository(database_path) as repository:
        assert repository.get_history(conversation_id).conversation.revision == 1

    button(app, "Nova conversa").click().run()
    assert not app.exception
    assert app.session_state["conversation_id"] != conversation_id
    assert len(app.chat_message) == 1

    resumed = open_app()
    resumed.selectbox(key="conversation_id").select(conversation_id).run()
    assert len(resumed.chat_message) == 2
    resumed.chat_input[0].set_value("Ainda penso nisso.").run()
    assert not resumed.exception
    assert "seu futuro" in resumed.chat_message[3].text[0].value
    with ConversationRepository(database_path) as repository:
        assert repository.get_history(conversation_id).conversation.revision == 2


def test_delete_requires_confirmation_and_preserves_other_conversation(database_path: Path) -> None:
    with ConversationRepository(database_path) as repository:
        target = repository.create_conversation("Excluir")
        other = repository.create_conversation("Manter")
        repository.append_turn(target.id, "Oi", "Olá", expected_revision=0)

    app = open_app()
    app.selectbox(key="conversation_id").select(target.id).run()
    button(app, "Excluir conversa").click().run()
    assert app.warning
    button(app, "Cancelar").click().run()
    assert not app.warning
    with ConversationRepository(database_path) as repository:
        assert repository.get_conversation(target.id) is not None

    button(app, "Excluir conversa").click().run()
    app.selectbox(key="conversation_id").select(other.id).run()
    assert not app.warning
    app.selectbox(key="conversation_id").select(target.id).run()
    button(app, "Excluir conversa").click().run()
    button(app, "Confirmar exclusão").click().run()
    assert not app.exception
    assert app.success[0].value == "Conversa excluída."
    assert app.selectbox(key="conversation_id").value is None
    with ConversationRepository(database_path) as repository:
        assert [item.id for item in repository.list_conversations()] == [other.id]


def test_invalid_input_keeps_history_and_allows_retry(database_path: Path) -> None:
    app = open_app()
    button(app, "Nova conversa").click().run()
    conversation_id = app.session_state["conversation_id"]
    app.chat_input[0].set_value("...").run()
    assert not app.exception
    assert app.warning
    with ConversationRepository(database_path) as repository:
        assert repository.get_history(conversation_id).messages == ()
    app.chat_input[0].set_value("Olá").run()
    assert len(app.chat_message) == 2
