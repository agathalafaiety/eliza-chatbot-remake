"""O chat público funciona e mantém o histórico separado por sessão."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

DEMO = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"


def test_demo_responds_with_isolated_history(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("A demonstração pública tentou abrir configurações, banco ou provedor local.")

    monkeypatch.setattr("eliza.config.load_settings", forbidden)
    monkeypatch.setattr("database.ConversationRepository.__init__", forbidden)
    monkeypatch.setattr("eliza.ai._generate", forbidden)

    first = AppTest.from_file(str(DEMO)).run()
    first.chat_input[0].set_value("Estou preocupado com meu futuro.").run()
    assert not first.exception
    assert len(first.chat_message) == 3
    assert "seu futuro" in first.chat_message[2].text[0].value

    second = AppTest.from_file(str(DEMO)).run()
    assert not second.exception
    assert len(second.chat_message) == 1
    second.chat_input[0].set_value("Olá!").run()
    first.run()
    assert "seu futuro" in first.chat_message[2].text[0].value

    first.sidebar.button[0].click().run()
    assert len(first.chat_message) == 1
    second.run()
    assert len(second.chat_message) == 3
