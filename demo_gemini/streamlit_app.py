"""Demonstração pública da ELIZA com Gemini e histórico no navegador."""

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from demo_gemini.history import (  # noqa: E402
    MAX_CONVERSATIONS,
    MAX_MESSAGE_LENGTH,
    MAX_TURNS,
    Conversation,
    browser_snapshot,
    delete_conversation,
    save_turn,
)
from demo_gemini.limits import SESSION_LIMIT, RequestBudget  # noqa: E402
from eliza.ai import GeminiError, generate_reply  # noqa: E402
from eliza.config import Settings  # noqa: E402

CONTEXT_TURNS = 4
STORAGE_ERRORS = {
    "conflict": "A conversa mudou em outra aba. Confira o histórico e tente novamente.",
    "full": "O histórico está cheio. Exclua uma conversa para liberar espaço.",
    "write": "Não foi possível gravar o histórico neste navegador.",
}


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


def select_conversation(history: list[Conversation]) -> Conversation | None:
    conversations = {item.id: item for item in history}
    labels: dict[str, str] = {}
    repeated: Counter[str] = Counter()
    for item in history:
        title = item.title
        repeated[title] += 1
        labels[item.id] = title if repeated[title] == 1 else f"{title} ({repeated[title]})"
    state = st.session_state
    with st.sidebar:
        st.header("Conversas")
        if st.button("Nova conversa", icon=":material/add:", width="stretch"):
            state.gemini_selected = None
            state.pop("gemini_delete", None)
        if state.get("gemini_selected") not in conversations:
            state.gemini_selected = None
        selected = st.selectbox(
            "Retomar conversa",
            list(conversations),
            index=None,
            key="gemini_selected",
            format_func=labels.__getitem__,
            placeholder="Selecione uma conversa" if history else "Nenhuma conversa salva",
        )
        if state.get("gemini_delete") != selected:
            state.pop("gemini_delete", None)
        if selected is not None:
            if st.button("Excluir conversa"):
                state.gemini_delete = selected
            if state.get("gemini_delete") == selected:
                st.warning("Excluir esta conversa do navegador?")
                if st.button("Cancelar"):
                    state.pop("gemini_delete", None)
                    st.rerun()
                if st.button("Confirmar exclusão"):
                    state.gemini_command = delete_conversation(selected)
                    state.pop("gemini_delete", None)
                    st.rerun()
        return conversations.get(selected)


def main() -> None:
    st.set_page_config(page_title="ELIZA com Gemini", page_icon=":material/chat:")
    st.title("ELIZA com Gemini")
    st.caption(
        "Uma simulação conversacional em português, inspirada na ELIZA de Joseph Weizenbaum."
    )
    st.caption(
        "As conversas ficam salvas neste navegador, sem sincronização. Ao enviar uma mensagem, "
        "você compartilha o texto e parte da conversa selecionada com o Google Gemini. "
        "Evite enviar dados pessoais."
    )
    state = st.session_state
    command = state.get("gemini_command")
    snapshot = browser_snapshot(command)
    if snapshot is None:
        st.info("Carregando conversas deste navegador…")
        return
    if snapshot.unavailable:
        st.error("Não foi possível carregar o histórico. Confira o armazenamento do navegador.")
        return
    if command is not None:
        if snapshot.command_id != command["id"]:
            st.info("Salvando a alteração…")
            return
        state.pop("gemini_command")
        if snapshot.error is not None:
            st.warning(STORAGE_ERRORS[snapshot.error])
        elif command["operation"] == "save":
            state.gemini_selected = command["conversationId"]

    conversation = select_conversation(snapshot.history)
    turns = conversation.turns if conversation else []

    settings = read_settings()
    remaining = SESSION_LIMIT - state.get("gemini_attempts", 0)
    st.sidebar.caption(f"Mensagens disponíveis nesta sessão: {remaining}")
    show_message(Message("assistant", "Olá, sou a ELIZA. Sobre o que gostaria de conversar?"))
    for turn in turns:
        show_message(Message("user", turn.user))
        show_message(Message("assistant", turn.assistant))
    if notice := state.pop("gemini_notice", None):
        st.warning(notice)

    history_full = conversation is None and len(snapshot.history) >= MAX_CONVERSATIONS
    conversation_full = len(turns) >= MAX_TURNS
    if settings.gemini_api_key is None:
        st.info("O Gemini ainda não está configurado nesta demo.")
    elif not remaining:
        st.info("Você atingiu o limite de mensagens desta sessão.")
    elif history_full:
        st.info("Você atingiu o limite de conversas salvas. Exclua uma para criar outra.")
    elif conversation_full:
        st.info("Esta conversa atingiu o limite de mensagens. Abra uma nova para continuar.")
    submitted = st.chat_input(
        "Escreva sua mensagem",
        max_chars=MAX_MESSAGE_LENGTH,
        disabled=settings.gemini_api_key is None
        or not remaining
        or history_full
        or conversation_full,
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

    context = tuple(
        message
        for turn in turns[-CONTEXT_TURNS:]
        for message in (Message("user", turn.user), Message("assistant", turn.assistant))
    )
    state.gemini_attempts = state.get("gemini_attempts", 0) + 1
    with st.spinner("ELIZA está respondendo...", show_time=True):
        try:
            reply = generate_reply(settings, context, message_text)
        except GeminiError:
            state.gemini_notice = (
                "O Gemini não conseguiu responder agora. Tente novamente em instantes."
            )
        else:
            state.gemini_command = save_turn(conversation, message_text, reply)
    st.rerun()


if __name__ == "__main__":
    main()
