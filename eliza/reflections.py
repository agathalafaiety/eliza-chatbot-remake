"""Substituições de pessoa em uma única passagem, sem geração de linguagem."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Literal

Language = Literal["pt-BR"]

REFLECTIONS_PT = {
    "eu estou": "você está",
    "eu sou": "você é",
    "eu tenho": "você tem",
    "eu sinto": "você sente",
    "eu quero": "você quer",
    "eu preciso": "você precisa",
    "eu posso": "você pode",
    "você está": "eu estou",
    "voce esta": "eu estou",
    "você é": "eu sou",
    "voce e": "eu sou",
    "você tem": "eu tenho",
    "voce tem": "eu tenho",
    "comigo": "com você",
    "contigo": "comigo",
    "meu": "seu",
    "minha": "sua",
    "meus": "seus",
    "minhas": "suas",
    "seu": "meu",
    "sua": "minha",
    "seus": "meus",
    "suas": "minhas",
    "mim": "você",
    "eu": "você",
    "você": "eu",
    "voce": "eu",
}


def normalize_language(language: str) -> Language:
    if not isinstance(language, str):
        raise TypeError("O idioma deve ser uma string.")
    aliases: dict[str, Language] = {"pt": "pt-BR", "pt-br": "pt-BR"}
    try:
        return aliases[language.strip().casefold()]
    except KeyError:
        raise ValueError(
            "Este projeto usa somente português brasileiro. Use 'pt-BR' ou 'pt'."
        ) from None


def normalize_text(text: str) -> str:
    """Normaliza espaços, apóstrofos e acentos compostos sem retirar diacríticos."""
    if not isinstance(text, str):
        raise TypeError("O texto deve ser uma string.")
    text = unicodedata.normalize("NFC", text).replace("’", "'").replace("‘", "'")
    return " ".join(text.split())


@lru_cache(maxsize=1)
def _reflection_pattern() -> re.Pattern[str]:
    substitutions = REFLECTIONS_PT
    alternatives = "|".join(re.escape(key) for key in sorted(substitutions, key=len, reverse=True))
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.IGNORECASE)


def reflect(text: str, language: str = "pt-BR") -> str:
    """Troca pessoa/pronomes sem substituir trechos internos de outras palavras.

    Expressões maiores têm precedência. Substituições não são processadas de novo:
    'meu' vira 'seu', sem retornar a 'meu'. Não é um analisador gramatical completo.
    """
    normalize_language(language)
    normalized = normalize_text(text)
    substitutions = REFLECTIONS_PT
    return _reflection_pattern().sub(
        # IGNORECASE também aceita letras Unicode como 'ı'. Caso não exista
        # uma chave equivalente, preserva a palavra em vez de falhar.
        lambda match: substitutions.get(match.group().casefold(), match.group()),
        normalized,
    )
