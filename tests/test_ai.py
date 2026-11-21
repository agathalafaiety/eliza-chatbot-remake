"""Contrato da API Gemini com SDK real e transporte HTTP simulado."""

import json
from pathlib import Path

import pytest
from pydantic import SecretStr

from database import ConversationRepository
from eliza.ai import GeminiError, send_ai_turn
from eliza.config import Settings

httpx2 = pytest.importorskip("httpx2")
genai = pytest.importorskip("google.genai")
Client = genai.Client


@pytest.fixture
def intercept_api(monkeypatch):
    def install(handler, *, use_app_retry=False):
        def client(**options):
            if not use_app_retry:
                options["http_options"].retry_options.attempts = 1
            options["http_options"].httpx_client = httpx2.Client(
                transport=httpx2.MockTransport(handler)
            )
            return Client(**options)

        monkeypatch.setattr("google.genai.Client", client)

    return install


def test_ai_sends_bounded_history_and_saves_reply(tmp_path: Path, intercept_api) -> None:
    def respond(request: httpx2.Request) -> httpx2.Response:
        assert str(request.url) == (
            "https://generativelanguage.googleapis.com/v1beta/models/modelo-configurado:generateContent"
        )
        assert request.headers["x-goog-api-key"] == "teste-sem-rede"
        payload = json.loads(request.content)
        assert payload["generationConfig"]["maxOutputTokens"] == 512
        assert "thinkingConfig" not in payload["generationConfig"]
        assert "português brasileiro" in payload["systemInstruction"]["parts"][0]["text"]
        assert payload["contents"] == [
            {"role": "user", "parts": [{"text": "Falei sobre meu trabalho."}]},
            {"role": "model", "parts": [{"text": "O que mais preocupa você?"}]},
            {"role": "user", "parts": [{"text": "Os prazos."}]},
        ]
        return httpx2.Response(
            200,
            json={
                "candidates": [
                    {"content": {"role": "model", "parts": [{"text": "Qual prazo preocupa você?"}]}}
                ]
            },
        )

    intercept_api(respond)
    settings = Settings(
        gemini_api_key=SecretStr("teste-sem-rede"), gemini_model="modelo-configurado"
    )
    with ConversationRepository(tmp_path / "ai.db") as repo:
        conversation = repo.create_conversation(mode="ai")
        repo.append_turn(conversation.id, "a" * 6500, "b" * 6500, expected_revision=0)
        repo.append_turn(
            conversation.id,
            "Falei sobre meu trabalho.",
            "O que mais preocupa você?",
            expected_revision=1,
        )
        turn = send_ai_turn(repo, settings, conversation.id, "Os prazos.")
        assert turn.assistant.content == "Qual prazo preocupa você?"
        assert repo.get_history(conversation.id).messages[-2:] == (turn.user, turn.assistant)


def test_flash_lite_recovers_from_504_and_saves_one_turn(tmp_path: Path, intercept_api) -> None:
    attempts = 0

    def respond(request: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        assert request.url.path.endswith("gemini-3.5-flash-lite:generateContent")
        config = json.loads(request.content)["generationConfig"]
        assert config["thinkingConfig"] == {"thinking_level": "MINIMAL"}
        if attempts == 1:
            return httpx2.Response(504, json={"error": {"code": 504, "message": "Gateway timeout"}})
        return httpx2.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": "Sobre o que você gostaria de conversar?"}],
                        }
                    }
                ]
            },
        )

    intercept_api(respond, use_app_retry=True)
    with ConversationRepository(tmp_path / "flash-lite.db") as repo:
        conversation = repo.create_conversation(mode="ai")
        settings = Settings(gemini_api_key=SecretStr("teste-sem-rede"))
        assert send_ai_turn(repo, settings, conversation.id, "Olá").assistant.content
        assert attempts == 2
        assert len(repo.get_history(conversation.id).messages) == 2


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "Confira GEMINI_API_KEY"),
        (429, "limite de uso"),
        (503, "temporariamente indisponível"),
        (504, "temporariamente indisponível"),
        (200, "não retornou texto"),
    ],
)
def test_api_failure_keeps_history_and_hides_provider_details(
    tmp_path: Path,
    intercept_api,
    status: int,
    message: str,
) -> None:
    payload = (
        {"candidates": []}
        if status == 200
        else {"error": {"code": status, "message": "DETALHE PRIVADO"}}
    )
    intercept_api(lambda request: httpx2.Response(status, json=payload))
    settings = Settings(gemini_api_key=SecretStr("teste-sem-rede"))
    with ConversationRepository(tmp_path / "failure.db") as repo:
        conversation = repo.create_conversation(mode="ai")
        with pytest.raises(GeminiError, match=message) as error:
            send_ai_turn(repo, settings, conversation.id, "Olá")
        assert "DETALHE PRIVADO" not in str(error.value)
        assert repo.get_history(conversation.id).messages == ()
