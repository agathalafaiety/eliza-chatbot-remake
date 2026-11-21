"""Demonstração pública da ELIZA Classic com histórico por sessão."""

import sys
from pathlib import Path

import streamlit as st

# O executável Streamlit acrescenta a pasta deste script ao caminho de importação.
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from eliza import ClassicEliza  # noqa: E402


def main() -> None:
    st.set_page_config(page_title="ELIZA Classic", page_icon=":material/chat:")
    st.title("ELIZA Classic")
    st.caption("Uma recriação em português brasileiro da ELIZA de Joseph Weizenbaum.")
    st.caption("O histórico fica disponível durante esta sessão.")

    if "demo_classic" not in st.session_state:
        st.session_state.demo_classic = ClassicEliza()
    eliza: ClassicEliza = st.session_state.demo_classic
    if st.sidebar.button("Nova conversa", icon=":material/add:", width="stretch"):
        eliza.reset()

    with st.chat_message("ELIZA", avatar=":material/chat:"):
        st.text(eliza.welcome_message)

    for turn in eliza.history:
        with st.chat_message("Você", avatar=":material/person:"):
            st.text(turn.user)
        with st.chat_message("ELIZA", avatar=":material/chat:"):
            st.text(turn.assistant)

    message = st.chat_input("Escreva sua mensagem", max_chars=ClassicEliza.MAX_MESSAGE_LENGTH)
    if message is not None:
        try:
            eliza.respond(message)
        except ValueError as error:
            st.warning(str(error))
        else:
            st.rerun()


if __name__ == "__main__":
    main()
