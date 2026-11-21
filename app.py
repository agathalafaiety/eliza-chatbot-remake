"""Entrada da interface web do ELIZA Classic."""

import streamlit as st
from pydantic import ValidationError

from database import ConversationNotFoundError, ConversationRepository, StorageError
from eliza.config import load_settings
from ui.chat import render_chat
from ui.sidebar import render_sidebar


def main() -> None:
    st.set_page_config(page_title="ELIZA Chatbot Remake", page_icon=":material/chat:")
    st.title("ELIZA Chatbot Remake")
    st.caption("Classic · Português brasileiro · Offline")
    st.caption("ELIZA é uma simulação conversacional baseada em regras.")

    try:
        path = load_settings().database_path()
    except ValidationError:
        st.error("Configuração do banco inválida. Confira ELIZA_DATABASE_URL.")
        return
    if path == ":memory:":
        st.error("Configure um arquivo SQLite em ELIZA_DATABASE_URL para salvar as conversas.")
        return

    notice = st.session_state.pop("notice", None)
    if notice:
        st.success(notice)

    try:
        with ConversationRepository(path) as repository:
            conversation_id = render_sidebar(repository)
            render_chat(repository, conversation_id)
    except ConversationNotFoundError:
        st.session_state.pop("conversation_id", None)
        st.session_state.pop("delete_target", None)
        st.warning("Esta conversa foi excluída. Atualize a lista para continuar.")
        if st.button("Atualizar conversas"):
            st.rerun()
    except StorageError as error:
        st.error(str(error))


if __name__ == "__main__":
    main()
