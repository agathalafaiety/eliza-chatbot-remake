"""Comportamento público, limites de sessão e execução efetivamente offline."""

from __future__ import annotations

import subprocess
import sys
import unicodedata
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from eliza import ClassicEliza


@pytest.mark.parametrize(
    ("message", "rule"),
    [
        ("Olá!", "greeting"),
        ("Oi, ELIZA!", "greeting"),
        ("ola", "greeting"),
        ("bom dia", "greeting"),
        ("Até logo!", "farewell"),
        ("Estou preocupado com meu futuro.", "worried"),
        ("Estou preocupada com minha carreira.", "worried"),
        ("Tenho medo de fracassar.", "fear"),
        ("Tenho medo da minha mãe.", "fear"),
        ("Esse medo aparece às vezes.", "fear_general"),
        ("Eu me sinto triste.", "feeling"),
        ("Não consigo dormir.", "inability"),
        ("Nao consigo estudar.", "inability"),
        ("Preciso de apoio.", "need"),
        ("Gostaria de mudar de emprego.", "desire"),
        ("Quero um emprego.", "desire"),
        ("Estou triste.", "state"),
        ("Eu sou estudante.", "self"),
        ("Minha mãe trabalha muito.", "family"),
        ("Minha mae trabalha muito.", "family"),
        ("Sonhei com minha casa.", "dream"),
        ("Porque isso importa.", "reason"),
        ("Isso sempre acontece.", "always"),
        ("Gosto de computadores.", "computer"),
        ("sim", "yes"),
        ("não", "no"),
        ("Como isso funciona?", "question"),
        ("As nuvens mudaram de cor.", "fallback"),
    ],
)
def test_portuguese_patterns(message: str, rule: str) -> None:
    response = ClassicEliza().reply(message)
    assert response.rule_id == rule
    assert response.text
    assert "{fragment}" not in response.text


def test_fragment_uses_reflection_and_stops_at_sentence_boundary() -> None:
    reply = ClassicEliza().reply("Estou preocupado com meu futuro. Minha mãe também.")
    assert reply.text == "O que preocupa você em relação a seu futuro?"
    assert reply.fragment == "seu futuro"
    assert reply.rule_id == "worried"


def test_preserves_accents_and_accepts_unusual_spacing() -> None:
    message = unicodedata.normalize("NFD", "  ESTOU\n preocupada   com minha mãe. ")
    reply = ClassicEliza().reply(message)
    assert reply.fragment == "sua mãe"


@pytest.mark.parametrize(
    "message", ["Você é psicóloga?", "Voce e uma pessoa?", "Quem é você?", "Você é meu terapeuta?"]
)
def test_identity_is_honest_and_has_priority_over_questions(message: str) -> None:
    reply = ClassicEliza().reply(message)
    assert reply.rule_id == "identity"
    assert "simulação" in reply.text
    assert "Não sou profissional de saúde" in reply.text


def test_welcome_is_not_an_extra_history_turn() -> None:
    bot = ClassicEliza()
    assert "simulação" in bot.welcome_message
    assert bot.history == ()


@pytest.mark.parametrize("language", ["en", "es"])
def test_other_language_configuration_is_rejected(language: str) -> None:
    with pytest.raises(ValueError, match="somente português"):
        ClassicEliza(language)


def test_specific_rules_precede_generic_state_and_family() -> None:
    bot = ClassicEliza()
    assert bot.reply("Estou preocupada com minha família.").rule_id == "worried"
    assert bot.reply("Me sinto triste por minha mãe.").rule_id == "feeling"


@pytest.mark.parametrize(
    "message",
    [
        "Não quero fracassar.",
        "Nao estou preocupado com meu futuro.",
        "Não tenho medo de fracassar.",
        "Nunca estou triste.",
        "Não preciso de ajuda.",
    ],
)
def test_portuguese_negation_is_not_treated_as_affirmative_desire_or_state(message: str) -> None:
    assert ClassicEliza().reply(message).rule_id == "negation"


def test_rotation_is_per_rule_and_reproducible() -> None:
    messages = [
        "Estou preocupado com meu futuro.",
        "Estou preocupado com meu trabalho.",
        "Estou preocupado com meu estudo.",
    ]
    first, second = ClassicEliza(), ClassicEliza()
    responses = [first.respond(message) for message in messages]
    assert responses == [second.respond(message) for message in messages]
    assert responses[0].startswith("O que preocupa")
    assert responses[1].startswith("O que poderia ajudar")
    assert responses[2].startswith("O que preocupa")


def test_repeated_input_has_alternative_reflective_responses() -> None:
    bot = ClassicEliza()
    bot.respond("Tenho medo de fracassar.")
    first = bot.reply("TENHO medo de fracassar!")
    second = bot.reply("Tenho medo de fracassar")
    assert first.rule_id == second.rule_id == "repetition"
    assert first.text != second.text


@pytest.mark.parametrize(
    ("language", "message", "topic"),
    [
        ("pt-BR", "Estou preocupado com meu futuro.", "seu futuro"),
    ],
)
def test_memory_refers_to_previous_topic_and_alternates_with_fallback(
    language: str, message: str, topic: str
) -> None:
    bot = ClassicEliza(language)
    bot.respond(message)
    memory = bot.reply("xyz abc")
    assert memory.rule_id == "memory"
    assert topic in memory.text
    assert bot.reply("xyz def").rule_id == "fallback"
    assert bot.reply("xyz ghi").rule_id == "memory"


def test_a_new_topic_replaces_old_topic() -> None:
    bot = ClassicEliza()
    bot.respond("Estou preocupado com meu futuro.")
    bot.respond("Tenho medo de perder meu trabalho.")
    reply = bot.reply("hmm")
    assert "perder seu trabalho" in reply.text
    assert "futuro" not in reply.text


def test_sessions_do_not_share_memory_or_response_rotation() -> None:
    first, second = ClassicEliza(), ClassicEliza()
    first.respond("Tenho medo de fracassar.")
    assert second.reply("hmm").rule_id == "fallback"
    assert first.reply("hmm").rule_id == "memory"
    assert second.history[0].user == "hmm"


def test_reset_clears_topic_history_rotation_and_repetition() -> None:
    bot = ClassicEliza()
    original = bot.respond("Estou preocupado com meu futuro.")
    bot.respond("Estou preocupado com meu trabalho.")
    bot.reset()
    assert bot.history == ()
    assert bot.reply("hmm").rule_id == "fallback"
    bot.reset()
    assert bot.respond("Estou preocupado com meu futuro.") == original


def test_history_is_bounded_and_read_only() -> None:
    bot = ClassicEliza(history_limit=2)
    for message in ("oi", "sim", "não"):
        bot.respond(message)
    assert [turn.user for turn in bot.history] == ["sim", "não"]
    with pytest.raises(FrozenInstanceError):
        bot.history[0].user = "outro texto"  # type: ignore[misc]


def test_fallback_does_not_match_partial_keywords() -> None:
    bot = ClassicEliza()
    assert bot.reply("O papaiol contém palha.").rule_id == "fallback"


@pytest.mark.parametrize("message", ["", " \n\t", "...", "?!;"])
def test_empty_message_is_rejected_without_changing_session(message: str) -> None:
    bot = ClassicEliza()
    with pytest.raises(ValueError, match="conteúdo"):
        bot.respond(message)
    assert bot.history == ()


def test_long_message_is_rejected_before_matching() -> None:
    bot = ClassicEliza()
    with pytest.raises(ValueError, match="4000"):
        bot.respond("x" * 4001)
    assert bot.history == ()
    assert bot.reply("x" * 4000).rule_id == "fallback"


@pytest.mark.parametrize("limit", [0, -1, 1001])
def test_invalid_history_limit(limit: int) -> None:
    with pytest.raises(ValueError):
        ClassicEliza(history_limit=limit)


@pytest.mark.parametrize("limit", [True, 1.5, "20"])
def test_non_integer_history_limit(limit: object) -> None:
    with pytest.raises(TypeError):
        ClassicEliza(history_limit=limit)  # type: ignore[arg-type]


def test_invalid_types_and_language_are_explicit() -> None:
    with pytest.raises(TypeError):
        ClassicEliza().respond(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ClassicEliza("es")


def test_topic_memory_does_not_grow_with_message_length() -> None:
    bot = ClassicEliza()
    bot.respond("Estou preocupado com " + "futuro " * 100)
    reply = bot.reply("hmm")
    assert reply.fragment is not None
    assert len(reply.fragment) <= bot.MAX_TOPIC_LENGTH


def test_untrusted_text_is_not_executed(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist.txt"
    payload = f"__import__('pathlib').Path({str(marker)!r}).touch()"
    assert ClassicEliza().respond(payload)
    assert not marker.exists()


def test_classic_runs_without_site_packages_api_key_or_network() -> None:
    # -I -S desativa site-packages e variáveis Python. O processo importa somente
    # a biblioteca padrão e o pacote local, com criação de sockets proibida.
    root = Path(__file__).resolve().parents[1]
    code = """
import os
import socket
import sys

sys.path.insert(0, sys.argv[1])
os.environ.pop('GOOGLE_API_KEY', None)
os.environ.pop('GEMINI_API_KEY', None)

def forbidden(*args, **kwargs):
    raise AssertionError('Classic tentou acessar a rede')

socket.socket = forbidden
socket.create_connection = forbidden
from eliza import ClassicEliza

bot = ClassicEliza()
assert bot.reply('Estou preocupado com meu futuro.').rule_id == 'worried'
assert bot.reply('Tenho medo de fracassar.').rule_id == 'fear'
assert bot.reply('hmm').rule_id == 'memory'
assert not any(name in sys.modules for name in ('streamlit', 'sqlalchemy', 'chromadb', 'google'))
print('offline OK')
"""
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code, str(root)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "offline OK" in result.stdout
