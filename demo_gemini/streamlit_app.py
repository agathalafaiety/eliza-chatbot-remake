"""Demonstração pública da ELIZA com Gemini e histórico por sessão."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from demo_gemini.limits import SESSION_LIMIT, RequestBudget  # noqa: E402
from eliza.ai import GeminiError, generate_reply  # noqa: E402
from eliza.config import Settings  # noqa: E402

MAX_MESSAGE_LENGTH = 1000
CONTEXT_MESSAGES = 8


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    content: str


@st.cache_resource
def request_budget() -> RequestBudget:
    return RequestBudget()


def read_settings() -> Settings:
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except StreamlitSecretNotFoundError:
        key = ""
    key = key.strip() if isinstance(key, str) else ""
    return Settings(gemini_api_key=key or None)


def show_message(message: Message) -> None:
    name, avatar = (
        ("Você", ":material/person:") if message.role == "user" else ("ELIZA", ":material/chat:")
    )
    with st.chat_message(name, avatar=avatar):
        st.text(message.content)


def main() -> None:
    st.set_page_config(page_title="ELIZA com Gemini", page_icon=":material/chat:")
    st.title("ELIZA com Gemini")
    st.caption(
        "Uma simulação conversacional em português, inspirada na ELIZA de Joseph Weizenbaum."
    )
    st.caption(
        "O histórico fica na sessão. Ao enviar uma mensagem, você compartilha o texto "
        "e parte da conversa recente com o Google Gemini. Evite enviar dados pessoais."
    )
    if "gemini_messages" not in st.session_state:
        st.session_state.gemini_messages = []
        st.session_state.gemini_attempts = 0
    history: list[Message] = st.session_state.gemini_messages
    if st.sidebar.button("Nova conversa", icon=":material/add:", width="stretch"):
        history.clear()

    settings = read_settings()
    remaining = SESSION_LIMIT - st.session_state.gemini_attempts
    st.sidebar.caption(f"Mensagens disponíveis nesta sessão: {remaining}")
    show_message(Message("assistant", "Olá, sou a ELIZA. Sobre o que gostaria de conversar?"))
    for message in history:
        show_message(message)
    if notice := st.session_state.pop("gemini_notice", None):
        st.warning(notice)

    if settings.gemini_api_key is None:
        st.info("O Gemini ainda não está configurado nesta demo.")
    elif not remaining:
        st.info("Você atingiu o limite de mensagens desta sessão.")
    submitted = st.chat_input(
        "Escreva sua mensagem",
        max_chars=MAX_MESSAGE_LENGTH,
        disabled=settings.gemini_api_key is None or not remaining,
    )
    if submitted is None:
        return
    message_text = submitted.strip()
    if not message_text or len(message_text) > MAX_MESSAGE_LENGTH:
        st.warning(f"Digite uma mensagem com até {MAX_MESSAGE_LENGTH} caracteres.")
        return
    limit = request_budget().reserve()
    if limit is not None:
        st.warning(limit)
        return

    st.session_state.gemini_attempts += 1
    with st.spinner("ELIZA está respondendo...", show_time=True):
        try:
            reply = generate_reply(settings, tuple(history[-CONTEXT_MESSAGES:]), message_text)
        except GeminiError:
            st.session_state.gemini_notice = (
                "O Gemini não conseguiu responder agora. Tente novamente em instantes."
            )
        else:
            history.extend((Message("user", message_text), Message("assistant", reply)))
    st.rerun()


if __name__ == "__main__":
    main()
