"""Exibe o histórico e encaminha novas mensagens à memória do Classic."""

import streamlit as st

from database import ConversationRepository
from eliza import ClassicEliza
from eliza.memory import ConversationMemory


def _message(role: str, content: str) -> None:
    is_user = role == "user"
    name = "Você" if is_user else "ELIZA"
    avatar = ":material/person:" if is_user else ":material/chat:"
    with st.chat_message(name, avatar=avatar):
        st.caption(name)
        st.text(content)


def render_chat(repository: ConversationRepository, conversation_id: str | None) -> None:
    if conversation_id is None:
        _message("assistant", ClassicEliza().welcome_message)
        st.info("Crie uma conversa ou escolha uma do histórico na barra lateral.")
        return

    saved = repository.get_history(conversation_id)
    st.text(saved.conversation.title)
    if not saved.messages and saved.conversation.mode == "classic":
        _message("assistant", ClassicEliza().welcome_message)
    for message in saved.messages:
        _message(message.role, message.content)

    if saved.conversation.mode != "classic":
        st.info(
            "Esta conversa está disponível para leitura. Para enviar mensagens, abra uma Classic."
        )
        return

    message = st.chat_input(
        "Escreva sua mensagem",
        max_chars=ClassicEliza.MAX_MESSAGE_LENGTH,
        key=f"message_{conversation_id}",
    )
    if message is not None:
        try:
            with st.spinner("ELIZA está respondendo…"):
                ConversationMemory(repository).send(conversation_id, message)
        except ValueError as error:
            st.warning(str(error))
        else:
            st.rerun()
