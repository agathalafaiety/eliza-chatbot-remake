"""Adaptador opcional da API Gemini para o modo ELIZA IA."""

import logging
from importlib.util import find_spec

from database import ConversationRepository, SavedTurn, StoredMessage
from eliza.classic import ClassicEliza
from eliza.config import Settings

logger = logging.getLogger(__name__)

MAX_CONTEXT_TURNS = 10
MAX_HISTORY_CHARS = 12_000
MAX_OUTPUT_TOKENS = 512
WELCOME = "Olá, sou a ELIZA no modo IA. Sobre o que você gostaria de conversar?"
INSTRUCTIONS = (
    "Você é ELIZA, uma simulação conversacional inspirada no roteiro DOCTOR. "
    "Responda sempre em português brasileiro, de forma breve, educada e reflexiva. "
    "Use o contexto para formular uma pergunta aberta quando fizer sentido. "
    "Apresente-se como uma simulação se perguntarem. Não alegue ser profissional de saúde, "
    "não faça diagnósticos e não recomende tratamentos."
)


class GeminiError(RuntimeError):
    """Falha de configuração ou resposta que pode ser mostrada na interface."""


def unavailable_reason(settings: Settings) -> str | None:
    if not settings.gemini_api_key or not settings.gemini_api_key.get_secret_value().strip():
        return "Configure GEMINI_API_KEY no arquivo .env para habilitar o modo IA."
    if find_spec("google") is None or find_spec("google.genai") is None:
        return "Instale as dependências de requirements-ai.txt para habilitar o modo IA."
    return None


def _recent_history(messages: tuple[StoredMessage, ...]) -> tuple[StoredMessage, ...]:
    """Seleciona um sufixo de turnos completos sem cortar mensagens no meio."""
    start = len(messages)
    chars = 0
    for end in range(len(messages), max(0, len(messages) - MAX_CONTEXT_TURNS * 2), -2):
        user, assistant = messages[end - 2 : end]
        chars += len(user.content) + len(assistant.content)
        if chars > MAX_HISTORY_CHARS:
            break
        start = end - 2
    return messages[start:]


def _generate(settings: Settings, history: tuple[StoredMessage, ...], message: str) -> str:
    reason = unavailable_reason(settings)
    if reason:
        raise GeminiError(reason)

    from google import genai
    from google.genai import errors, types
    from httpx2 import HTTPError

    assert settings.gemini_api_key is not None
    contents = [
        types.Content(
            role="user" if item.role == "user" else "model",
            parts=[types.Part(text=item.content)],
        )
        for item in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    config = types.GenerateContentConfig(
        system_instruction=INSTRUCTIONS,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    if settings.gemini_model.removeprefix("models/") in (
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
    ):
        config.thinking_config = types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)
    try:
        with genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(),
            enterprise=False,
            http_options=types.HttpOptions(
                base_url="https://generativelanguage.googleapis.com",
                api_version="v1beta",
                timeout=30_000,
                retry_options=types.HttpRetryOptions(
                    attempts=2, initial_delay=0.5, http_status_codes=[502, 503, 504]
                ),
            ),
        ) as client:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=config,
            )
    except (HTTPError, OSError):
        raise GeminiError("O Gemini não respondeu. Confira a conexão e tente novamente.") from None
    except errors.APIError as error:
        logger.warning("A API Gemini retornou HTTP %s.", error.code)
        messages = {
            400: "O Gemini recusou a solicitação. Confira GEMINI_API_KEY e GEMINI_MODEL.",
            401: "O Gemini recusou a chave. Confira GEMINI_API_KEY no arquivo .env.",
            403: "O Gemini recusou o acesso. Confira as permissões da chave e do modelo.",
            404: "Modelo indisponível. Confira GEMINI_MODEL e o acesso do seu projeto.",
            429: "O Gemini atingiu um limite de uso. Confira a cota ou tente novamente mais tarde.",
        }
        if error.code in (500, 502, 503, 504):
            raise GeminiError(
                "O Gemini está temporariamente indisponível. Tente novamente em instantes."
            ) from None
        raise GeminiError(messages.get(error.code, "O Gemini não pôde responder.")) from None

    reply = (response.text or "").strip()
    if not reply:
        raise GeminiError("O Gemini não retornou texto. Tente reformular a mensagem.")
    return reply


def send_ai_turn(
    repository: ConversationRepository, settings: Settings, conversation_id: str, message: str
) -> SavedTurn:
    """Gera a resposta fora da transação e grava o par na revisão que foi lida."""
    if not message.strip() or len(message) > ClassicEliza.MAX_MESSAGE_LENGTH:
        raise ValueError("Digite uma mensagem com conteúdo e até 4000 caracteres.")
    saved = repository.get_history(conversation_id)
    if saved.conversation.mode != "ai":
        raise ValueError("Abra uma conversa no modo IA para usar o Gemini.")
    if len(saved.messages) != saved.conversation.revision * 2:
        raise GeminiError("O histórico está incompleto. Abra uma nova conversa para continuar.")
    reply = _generate(settings, _recent_history(saved.messages), message)
    return repository.append_turn(
        conversation_id,
        message,
        reply,
        expected_revision=saved.conversation.revision,
    )
