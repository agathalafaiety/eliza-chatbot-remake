"""Regras autorais inspiradas em DOCTOR, ordenadas da mais específica à genérica."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    responses: tuple[str, ...]
    remember: bool = False


def _rule(name: str, pattern: str, *responses: str, remember: bool = False) -> Rule:
    return Rule(name, re.compile(pattern, re.IGNORECASE), responses, remember)


# Capturas são limitadas à oração, evitando englobar toda uma mensagem com várias frases.
FRAGMENT = r"(?P<fragment>[^.!?;]+)"


@lru_cache(maxsize=1)
def get_rules() -> tuple[Rule, ...]:
    return (
        _rule(
            "identity",
            r"\b(?:voc[eê] [eé] (?:uma? |meu |minha )?(?:pessoa|human[oa]|psic[oó]log[oa]|"
            r"terapeuta|m[eé]dic[oa])|quem [eé] voc[eê]|o que [eé] voc[eê])\b",
            "Sou uma simulação conversacional baseada em regras, sem compreensão humana. "
            "Não sou profissional de saúde. Sobre o que gostaria de conversar?",
            "Sou a ELIZA Classic, um programa de padrões textuais. "
            "Não sou uma pessoa nem profissional de saúde.",
        ),
        _rule(
            "farewell",
            r"^(?:tchau|adeus|at[eé] (?:logo|mais)|sair)[.!?]*$",
            "Até mais. Você pode voltar quando quiser conversar.",
            "Até a próxima. Obrigada pela conversa.",
        ),
        _rule(
            "greeting",
            r"^(?:oi|ol[aá]|bom dia|boa tarde|boa noite)(?:[, ]+eliza)?[.!?]*$",
            "Olá! Sobre o que gostaria de conversar hoje?",
            "Olá! O que está passando pela sua cabeça?",
        ),
        _rule(
            "negation",
            r"\b(?:n[aã]o|nunca) (?:estou|ando|sou|me sinto|quero|queria|preciso|"
            r"tenho medo|sinto medo)\b",
            "O que leva você a dizer isso?",
            "O que seria diferente se essa situação mudasse?",
        ),
        _rule(
            "worried",
            rf"\b(?:estou|ando|fico) preocupad[oa] (?:com|sobre) {FRAGMENT}",
            "O que preocupa você em relação a {fragment}?",
            "O que poderia ajudar você a lidar com essa preocupação sobre {fragment}?",
            remember=True,
        ),
        _rule(
            "fear",
            rf"\b(?:tenho|sinto) medo (?:de|da|do|das|dos) {FRAGMENT}",
            "O que mais assusta você em relação a {fragment}?",
            "Você poderia contar mais sobre esse medo relacionado a {fragment}?",
            remember=True,
        ),
        _rule(
            "fear_general",
            r"\bmedo\b",
            "Você poderia me contar mais sobre esse medo?",
            "Em que situações esse medo aparece?",
        ),
        _rule(
            "feeling",
            rf"\b(?:me sinto|sinto-me|estou me sentindo) {FRAGMENT}",
            "O que faz você se sentir {fragment}?",
            "Em que momentos você costuma se sentir {fragment}?",
            remember=True,
        ),
        _rule(
            "inability",
            rf"\bn[aã]o consigo {FRAGMENT}",
            "O que torna difícil para você {fragment}?",
            "O que você já tentou para conseguir {fragment}?",
            remember=True,
        ),
        _rule(
            "need",
            rf"\bpreciso (?:de )?{FRAGMENT}",
            "O que faz {fragment} ser importante para você?",
            "Como seria para você ter ou conseguir {fragment}?",
            remember=True,
        ),
        _rule(
            "desire",
            rf"\b(?:quero|queria|gostaria de) {FRAGMENT}",
            "O que significaria realizar esse desejo: {fragment}?",
            "O que motiva esse desejo: {fragment}?",
            remember=True,
        ),
        _rule(
            "state",
            rf"\b(?:estou|ando) {FRAGMENT}",
            "Você poderia contar mais sobre estar {fragment}?",
            "O que você associa a estar {fragment}?",
            remember=True,
        ),
        _rule(
            "self",
            rf"\b(?:eu )?sou {FRAGMENT}",
            "Como você se sente ao se descrever como {fragment}?",
            "O que significa para você se considerar {fragment}?",
            remember=True,
        ),
        _rule(
            "family",
            r"\b(?:m[aã]e|pai|fam[ií]lia|irm[aã]o|irm[aã]|filh[oa])\b",
            "Como você descreveria sua relação com sua família?",
            "O que mais gostaria de contar sobre sua família?",
        ),
        _rule(
            "dream",
            rf"\b(?:sonhei com|sonho com) {FRAGMENT}",
            "O que você associa a esse sonho com {fragment}?",
            "Que significado você atribui a sonhar com {fragment}?",
            remember=True,
        ),
        _rule(
            "reason",
            rf"\bporque {FRAGMENT}",
            "Que outros motivos você associa a isso?",
            "O que faz essa explicação parecer importante para você?",
        ),
        _rule(
            "always",
            r"\b(?:sempre|nunca)\b",
            "Você consegue pensar em alguma exceção?",
            "Que situação específica vem à sua cabeça quando diz isso?",
        ),
        _rule(
            "computer",
            r"\b(?:computador(?:es)?|rob[oô]s?|chatbot|intelig[eê]ncia artificial)\b",
            "O que você pensa sobre conversar com um programa de computador?",
            "O que desperta sua curiosidade sobre programas como este?",
        ),
        _rule(
            "yes",
            r"^(?:sim|claro|com certeza)[.!?]*$",
            "Você poderia desenvolver um pouco mais essa ideia?",
            "O que faz você concordar?",
        ),
        _rule(
            "no",
            r"^(?:n[aã]o|de jeito nenhum)[.!?]*$",
            "O que faz você dizer não?",
            "Como você chegou a essa conclusão?",
        ),
        _rule(
            "question",
            r"\?$",
            "O que levou você a fazer essa pergunta?",
            "Que resposta você imaginava para essa pergunta?",
        ),
    )
