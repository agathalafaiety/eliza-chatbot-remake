"""Exibe o histórico e responde no modo da conversa aberta."""

import streamlit as st

from database import ConversationRepository
from eliza import ClassicEliza
from eliza.ai import WELCOME, GeminiError, send_ai_turn
from eliza.config import Settings
from eliza.memory import ConversationMemory


def _message(role: str, content: str) -> None:
    is_user = role == "user"
    name = "Você" if is_user else "ELIZA"
    avatar = ":material/person:" if is_user else ":material/chat:"
    with st.chat_message(name, avatar=avatar):
        st.caption(name)
        st.text(content)


def render_chat(
    repository: ConversationRepository,
    conversation_id: str | None,
    settings: Settings,
    ai_unavailable: str | None,
) -> None:
    if conversation_id is None:
        _message("assistant", ClassicEliza().welcome_message)
        st.info("Crie uma conversa ou escolha uma do histórico na barra lateral.")
        return

    saved = repository.get_history(conversation_id)
    is_ai = saved.conversation.mode == "ai"
    st.text(saved.conversation.title)
    if is_ai:
        st.caption("Modo IA · A mensagem e parte do histórico recente são enviados ao Gemini.")
        if settings.semantic_memory:
            st.caption(
                "Memória semântica · Trechos antigos podem ser enviados ao Gemini para busca."
            )
    else:
        st.caption("Modo Classic · Respostas offline")
    if not saved.messages:
        _message("assistant", WELCOME if is_ai else ClassicEliza().welcome_message)
    for message in saved.messages:
        _message(message.role, message.content)

    if is_ai and ai_unavailable:
        st.info(ai_unavailable)
        return

    message = st.chat_input(
        "Escreva sua mensagem",
        max_chars=ClassicEliza.MAX_MESSAGE_LENGTH,
        key=f"message_{conversation_id}",
    )
    if message is not None:
        try:
            with st.spinner("ELIZA está respondendo…"):
                if is_ai:
                    send_ai_turn(repository, settings, conversation_id, message)
                else:
                    ConversationMemory(repository).send(conversation_id, message)
        except (ValueError, GeminiError) as error:
            st.warning(str(error))
        else:
            st.rerun()
