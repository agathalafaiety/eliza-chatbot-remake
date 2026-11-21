"""Mecanismo Classic, sem rede ou dependências externas.

Regras autorais inspiradas no conceito DOCTOR; não reproduzem integralmente o
script histórico. Uma instância corresponde a uma conversa em português brasileiro.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from eliza.patterns import get_rules
from eliza.personality import FALLBACK, MEMORY, REPETITION, WELCOME
from eliza.reflections import normalize_language, normalize_text, reflect


@dataclass(frozen=True)
class ClassicReply:
    text: str
    rule_id: str
    fragment: str | None = None


@dataclass(frozen=True)
class Turn:
    user: str
    assistant: str
    rule_id: str


class ClassicEliza:
    """Estado limitado a uma sessão: histórico curto, último tema e contadores.

    Respostas giram em ordem fixa por regra, tornando sessões reproduzíveis.
    `reply` inclui a regra para inspeção; `respond` devolve somente o texto.
    A memória de tema é uma substituição textual, sem inferência semântica.
    """

    MAX_MESSAGE_LENGTH = 4000
    MAX_TOPIC_LENGTH = 200

    def __init__(self, language: str = "pt-BR", *, history_limit: int = 20) -> None:
        if isinstance(history_limit, bool) or not isinstance(history_limit, int):
            raise TypeError("history_limit deve ser um inteiro.")
        if not 1 <= history_limit <= 1000:
            raise ValueError("history_limit deve estar entre 1 e 1000.")
        self._language = normalize_language(language)
        self._rules = get_rules()
        self._history: deque[Turn] = deque(maxlen=history_limit)
        self._counters: dict[str, int] = {}
        self._last_input: str | None = None
        self._topic: str | None = None
        self._unmatched_count = 0

    @property
    def language(self) -> str:
        return self._language

    @property
    def welcome_message(self) -> str:
        return WELCOME

    @property
    def history(self) -> tuple[Turn, ...]:
        return tuple(self._history)

    def reset(self) -> None:
        """Inicia uma sessão vazia, inclusive rotação de respostas e tema."""
        self._history.clear()
        self._counters.clear()
        self._last_input = None
        self._topic = None
        self._unmatched_count = 0

    def _select(self, key: str, alternatives: tuple[str, ...]) -> str:
        index = self._counters.get(key, 0)
        # O próprio contador também fica limitado à quantidade de alternativas.
        self._counters[key] = (index + 1) % len(alternatives)
        return alternatives[index]

    def respond(self, message: str) -> str:
        return self.reply(message).text

    def reply(self, message: str) -> ClassicReply:
        if not isinstance(message, str):
            raise TypeError("A mensagem deve ser uma string.")
        if len(message) > self.MAX_MESSAGE_LENGTH:
            raise ValueError(f"A mensagem deve ter no máximo {self.MAX_MESSAGE_LENGTH} caracteres.")
        normalized = normalize_text(message)
        canonical = normalized.casefold().rstrip(".!?;")
        if not canonical.strip():
            raise ValueError("Digite uma mensagem com conteúdo.")

        if canonical == self._last_input:
            response = ClassicReply(self._select("repetition", REPETITION), "repetition")
        else:
            response = self._match(normalized)
        self._last_input = canonical
        self._history.append(Turn(normalized, response.text, response.rule_id))
        return response

    def _match(self, message: str) -> ClassicReply:
        for rule in self._rules:
            match = rule.pattern.search(message)
            if match is None:
                continue
            captured = match.groupdict().get("fragment")
            fragment = reflect(captured.strip(" ,:"), self._language) if captured else None
            # Capturas só com espaços/pontuação não devem produzir perguntas vazias.
            if captured is not None and not fragment:
                continue
            template = self._select(rule.name, rule.responses)
            text = template.format(fragment=fragment)
            if rule.remember and fragment:
                self._topic = fragment[: self.MAX_TOPIC_LENGTH]
                self._unmatched_count = 0
            return ClassicReply(text, rule.name, fragment)

        # Alterna uma pergunta genérica e uma referência ao último tema disponível.
        use_memory = self._topic is not None and self._unmatched_count == 0
        self._unmatched_count = (self._unmatched_count + 1) % 2
        if use_memory:
            template = self._select("memory", MEMORY)
            return ClassicReply(template.format(fragment=self._topic), "memory", self._topic)
        return ClassicReply(self._select("fallback", FALLBACK), "fallback")
