import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from demo_gemini import history, limits
from eliza import ai


def open_demo(api_key: str = "chave-de-teste") -> AppTest:
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "demo_gemini/streamlit_app.py")
    app.secrets["GEMINI_API_KEY"] = api_key
    return app.run()


@pytest.fixture
def stored_conversations(monkeypatch):
    conversations = []

    def storage(data=None, **kwargs):
        command = data["command"]
        if command:
            conversation_id = command["conversationId"]
            conversations[:] = [item for item in conversations if item["id"] != conversation_id]
            if command["operation"] == "save":
                conversations.insert(0, command["conversation"])
        snapshot = {"history": conversations, "commandId": command["id"] if command else None}
        return SimpleNamespace(snapshot=json.dumps(snapshot))

    monkeypatch.setattr(history, "_bridge", storage)
    return conversations


@pytest.mark.usefixtures("stored_conversations")
def test_demo_disables_chat_without_secret():
    app = open_demo(api_key="")
    assert not app.exception
    assert app.chat_input[0].disabled
    assert "não está configurado" in app.info[0].value


def test_demo_saves_resumes_and_deletes_separate_conversations(monkeypatch, stored_conversations):
    st.cache_resource.clear()
    contexts = []

    def fake_generate(settings, history, message):
        contexts.append([item.content for item in history])
        return f"Você pode me contar mais sobre {message}?"

    monkeypatch.setattr(ai, "_generate", fake_generate)
    first = open_demo()
    first.chat_input[0].set_value("o futuro").run()
    assert len(first.chat_message) == 3
    first.sidebar.button[0].click().run()
    assert len(first.chat_message) == 1
    first.chat_input[0].set_value("os estudos").run()
    assert first.session_state.gemini_attempts == 2
    assert contexts == [[], []]
    assert len(stored_conversations) == 2

    reopened = open_demo()
    assert reopened.sidebar.selectbox[0].options == ["os estudos", "o futuro"]
    reopened.sidebar.selectbox[0].set_value(stored_conversations[1]["id"]).run()
    assert len(reopened.chat_message) == 3
    reopened.chat_input[0].set_value("meus planos").run()
    assert len(reopened.chat_message) == 5
    assert contexts[-1] == ["o futuro", "Você pode me contar mais sobre o futuro?"]

    reopened.sidebar.button[1].click().run()
    reopened.sidebar.button[3].click().run()
    assert not reopened.exception
    assert open_demo().sidebar.selectbox[0].options == ["os estudos"]


@pytest.mark.usefixtures("stored_conversations")
def test_demo_hides_provider_error_and_counts_failed_attempt(monkeypatch):
    st.cache_resource.clear()

    def fail(*args):
        raise ai.GeminiError("detalhe interno do provedor")

    monkeypatch.setattr(ai, "_generate", fail)
    app = open_demo()
    app.chat_input[0].set_value("Olá").run()
    assert not app.exception
    assert "Tente novamente" in app.warning[0].value
    assert "detalhe interno" not in app.warning[0].value
    assert len(app.chat_message) == 1
    assert app.session_state.gemini_attempts == 1


def test_demo_rejects_invalid_local_history(monkeypatch):
    monkeypatch.setattr(
        history, "_bridge", lambda **kwargs: SimpleNamespace(snapshot='{"history":[{"id":"x"}]}')
    )
    app = open_demo()
    assert not app.exception
    assert "Não foi possível carregar" in app.error[0].value
    assert not app.chat_input


def test_global_quota_uses_rolling_windows(monkeypatch):
    monkeypatch.setattr(limits, "MINUTE_LIMIT", 2)
    monkeypatch.setattr(limits, "DAILY_LIMIT", 3)
    now = 100.0
    monkeypatch.setattr(limits, "monotonic", lambda: now)
    budget = limits.RequestBudget()

    assert budget.reserve() is None
    assert budget.reserve() is None
    assert "instantes" in budget.reserve()
    now += 60
    assert budget.reserve() is None
    assert "diário" in budget.reserve()
    now += limits.DAY_SECONDS
    assert budget.reserve() is None
