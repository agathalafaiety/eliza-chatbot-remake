"""Substituições não podem perder acentos, atravessar palavras ou se reaplicar."""

import unicodedata

import pytest

from eliza.reflections import normalize_language, reflect


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("meu futuro", "seu futuro"),
        ("minha mãe e meus irmãos", "sua mãe e seus irmãos"),
        ("minhas escolhas e sua opinião", "suas escolhas e minha opinião"),
        ("eu estou preocupado", "você está preocupado"),
        ("eu sou estudante", "você é estudante"),
        ("eu tenho dúvidas", "você tem dúvidas"),
        ("você está comigo", "eu estou com você"),
        ("voce esta comigo", "eu estou com você"),
        ("mim, eu e você", "você, você e eu"),
        ("pneumonia, museu e europeia", "pneumonia, museu e europeia"),
        ("MEU futuro", "seu futuro"),
        ("  meu\n futuro  ", "seu futuro"),
        ("", ""),
    ],
)
def test_portuguese_reflections(source: str, expected: str) -> None:
    assert reflect(source) == expected


def test_decomposed_unicode_is_preserved_as_composed_text() -> None:
    source = unicodedata.normalize("NFD", "minha mãe")
    assert reflect(source) == "sua mãe"


@pytest.mark.parametrize(("source", "language"), [("mınha casa", "pt-BR")])
def test_unicode_case_variants_without_mapping_are_preserved(source: str, language: str) -> None:
    assert reflect(source, language) == source


@pytest.mark.parametrize(("source", "expected"), [("pt", "pt-BR"), (" PT-br ", "pt-BR")])
def test_language_aliases(source: str, expected: str) -> None:
    assert normalize_language(source) == expected


@pytest.mark.parametrize("language", ["en", "es"])
def test_unsupported_language_is_explicit(language: str) -> None:
    with pytest.raises(ValueError, match="somente português"):
        reflect("texto", language)


def test_non_text_is_rejected() -> None:
    with pytest.raises(TypeError, match="string"):
        reflect(None)  # type: ignore[arg-type]
