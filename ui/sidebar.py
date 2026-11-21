"""Criação, seleção e exclusão de conversas salvas."""

import streamlit as st

from database import ConversationRepository

PAGE_SIZE = 50


def render_sidebar(repository: ConversationRepository, ai_unavailable: str | None) -> str | None:
    with st.sidebar:
        st.header("Conversas")
        with st.form("new_conversation", clear_on_submit=True):
            title = st.text_input("Título (opcional)", max_chars=120)
            mode = st.radio(
                "Modo da nova conversa",
                ["Classic", "IA · Gemini"],
                disabled=ai_unavailable is not None,
            )
            if st.form_submit_button("Nova conversa", type="primary", width="stretch"):
                created = repository.create_conversation(
                    title.strip() or "Nova conversa",
                    mode="ai" if mode == "IA · Gemini" and ai_unavailable is None else "classic",
                )
                st.session_state["conversation_id"] = created.id
                st.session_state["history_page"] = 1
                st.session_state.pop("delete_target", None)
        if ai_unavailable:
            st.caption(ai_unavailable)

        current_page = st.session_state.get("history_page", 1)
        offset = (current_page - 1) * PAGE_SIZE
        page = repository.list_conversations(limit=PAGE_SIZE + 1, offset=offset)
        labels: dict[str, str] = {}
        for position, item in enumerate(page[:PAGE_SIZE], start=offset + 1):
            mode_label = "IA" if item.mode == "ai" else "Classic"
            label = f"{item.title} · {mode_label} · {item.created_at:%d/%m/%Y %H:%M} UTC"
            labels[item.id] = f"{label} ({position})" if label in labels.values() else label
        active = st.session_state.get("conversation_id")
        if active is not None and active not in labels:
            selected = repository.get_conversation(active)
            if selected is not None:
                labels[active] = f"{selected.title} · aberta"
            else:
                st.session_state.pop("conversation_id", None)

        conversation_id = st.selectbox(
            "Retomar conversa",
            list(labels),
            index=None,
            format_func=labels.__getitem__,
            placeholder="Selecione uma conversa" if labels else "Nenhuma conversa salva",
            key="conversation_id",
        )
        if current_page > 1 or len(page) > PAGE_SIZE:
            previous, following = st.columns(2)
            if previous.button("Anterior", disabled=current_page == 1):
                st.session_state["history_page"] = current_page - 1
                st.rerun()
            if following.button("Próxima", disabled=len(page) <= PAGE_SIZE):
                st.session_state["history_page"] = current_page + 1
                st.rerun()

        if st.session_state.get("delete_target") != conversation_id:
            st.session_state.pop("delete_target", None)
        if conversation_id is not None:
            _render_delete(repository, conversation_id)
        st.divider()
        st.caption("O histórico é salvo no SQLite neste computador.")
        return conversation_id


def _render_delete(repository: ConversationRepository, conversation_id: str) -> None:
    if st.button("Excluir conversa", key="delete_conversation"):
        st.session_state["delete_target"] = conversation_id
    if st.session_state.get("delete_target") != conversation_id:
        return

    st.warning("Excluir esta conversa e todas as suas mensagens?")
    if st.button("Cancelar", key="cancel_delete"):
        st.session_state.pop("delete_target", None)
        st.rerun()
    if st.button("Confirmar exclusão", key=f"confirm_delete_{conversation_id}", type="primary"):
        removed = repository.delete_conversation(conversation_id)
        st.session_state.pop("conversation_id", None)
        st.session_state.pop("delete_target", None)
        st.session_state["notice"] = (
            "Conversa excluída." if removed else "A conversa já foi excluída."
        )
        st.rerun()
