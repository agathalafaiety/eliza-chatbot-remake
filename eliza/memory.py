"""Integra Classic ao histórico persistente, sem alterar o mecanismo offline."""

from __future__ import annotations

from database import ConversationRepository, SavedConversation, SavedTurn, StorageError
from eliza.classic import ClassicEliza


class HistoryMismatchError(StorageError):
    """Não é seguro reconstruir a sessão com os dados/regras disponíveis."""


class ConversationMemory:
    """Coordena a retomada do Classic e a gravação de cada turno completo."""

    def __init__(self, repository: ConversationRepository) -> None:
        self.repository = repository

    @staticmethod
    def _restore(saved: SavedConversation) -> ClassicEliza:
        if saved.conversation.mode != "classic":
            raise ValueError("Esta etapa permite responder somente a conversas Classic.")
        if len(saved.messages) != saved.conversation.revision * 2:
            raise HistoryMismatchError("O histórico está incompleto.")
        bot = ClassicEliza(saved.conversation.language)
        for index in range(0, len(saved.messages), 2):
            user, assistant = saved.messages[index : index + 2]
            if (user.role, assistant.role, user.position, assistant.position) != (
                "user",
                "assistant",
                index,
                index + 1,
            ):
                raise HistoryMismatchError("A ordem do histórico é inválida.")
            try:
                reply = bot.reply(user.content)
            except (TypeError, ValueError):
                raise HistoryMismatchError("O histórico contém uma entrada inválida.") from None
            if reply.text != assistant.content or (
                assistant.rule_id is not None and reply.rule_id != assistant.rule_id
            ):
                raise HistoryMismatchError(
                    "O histórico não corresponde às regras atuais. "
                    "Você pode consultar o histórico ou criar outra conversa."
                )
        return bot

    def restore_classic(self, conversation_id: str) -> ClassicEliza:
        """Reproduz as entradas, preservando contadores, repetição e último tema."""
        return self._restore(self.repository.get_history(conversation_id))

    def send(self, conversation_id: str, message: str) -> SavedTurn:
        """Retoma a conversa, responde e salva o turno com a revisão que foi lida."""
        saved = self.repository.get_history(conversation_id)
        bot = self._restore(saved)
        reply = bot.reply(message)
        # O bot reconstruído só existe nesta chamada. Uma falha ou conflito não
        # avança uma sessão em memória nem deixa metade da interação no banco.
        return self.repository.append_turn(
            conversation_id,
            message,
            reply.text,
            rule_id=reply.rule_id,
            expected_revision=saved.conversation.revision,
        )
