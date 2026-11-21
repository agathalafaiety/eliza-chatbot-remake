"""Verifica o ambiente sem ler chaves ou fazer chamadas a provedores de IA."""

from __future__ import annotations

import argparse
import importlib
import platform
import sqlite3
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def check_base() -> None:
    """Confirma imports e gravação/leitura de SQLite via SQLAlchemy."""
    if sys.version_info < (3, 11):  # noqa: UP036 -- verifica o interpretador do usuário
        raise RuntimeError("Este projeto exige Python 3.11 ou mais recente.")

    print(f"Python: {platform.python_version()}")
    print(f"Interpretador: {sys.executable}")
    for module, package in (
        ("streamlit", "streamlit"),
        ("sqlalchemy", "SQLAlchemy"),
        ("dotenv", "python-dotenv"),
        ("pydantic", "pydantic"),
    ):
        importlib.import_module(module)
        print(f"{package}: {version(package)}")

    from sqlalchemy import URL, create_engine, text

    with tempfile.TemporaryDirectory(prefix="eliza-sqlite-") as directory:
        path = Path(directory) / "check.sqlite3"
        engine = create_engine(URL.create("sqlite", database=str(path)))
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE environment_check (message TEXT NOT NULL)"))
                connection.execute(
                    text("INSERT INTO environment_check (message) VALUES (:message)"),
                    {"message": "Olá, ELIZA!"},
                )
        finally:
            engine.dispose()

        reopened = create_engine(URL.create("sqlite", database=str(path)))
        try:
            with reopened.connect() as connection:
                result = connection.execute(
                    text("SELECT message FROM environment_check")
                ).scalar_one()
                if result != "Olá, ELIZA!":
                    raise RuntimeError("Falha na leitura do banco temporário.")
        finally:
            reopened.dispose()
    print(f"SQLite {sqlite3.sqlite_version}: gravação e reabertura via SQLAlchemy OK")


def check_notebook_dependencies() -> None:
    for module, package in (
        ("ipykernel", "ipykernel"),
        ("nbformat", "nbformat"),
        ("nbclient", "nbclient"),
        ("pytest", "pytest"),
    ):
        importlib.import_module(module)
        print(f"{package}: {version(package)}")
    print(f"Ruff: {version('ruff')}")


def check_optional_dependencies() -> None:
    # Importar o SDK não exige chave e não faz uma requisição à API.
    importlib.import_module("google.genai")
    print(f"SDK Gemini: {version('google-genai')} (importação OK; API não chamada)")

    # O cliente efêmero não cria dados permanentes. Vetores explícitos evitam
    # baixar um modelo de embeddings durante a verificação.
    import chromadb

    client = chromadb.EphemeralClient()
    collection_name = "eliza-environment-check"
    collection = client.create_collection(collection_name, embedding_function=None)
    try:
        collection.add(
            ids=["future", "music"],
            documents=["Estou preocupado com meu futuro.", "Gosto de ouvir música."],
            embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        )
        result = collection.query(query_embeddings=[[1.0, 0.0, 0.0]], n_results=1)
        if result["ids"] != [["future"]]:
            raise RuntimeError("A consulta vetorial de verificação falhou.")
        collection.delete(ids=["future", "music"])
        if collection.count() != 0:
            raise RuntimeError("A exclusão dos vetores de verificação falhou.")
    finally:
        client.delete_collection(collection_name)
    print(f"ChromaDB {version('chromadb')}: inclusão, consulta e exclusão de vetores OK")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebooks", action="store_true", help="Verifica ferramentas de notebook")
    parser.add_argument("--optional", action="store_true", help="Verifica SDK Gemini e ChromaDB")
    arguments = parser.parse_args()
    try:
        check_base()
        if arguments.notebooks:
            check_notebook_dependencies()
        if arguments.optional:
            check_optional_dependencies()
    except (ImportError, PackageNotFoundError):
        print(
            "Dependência ausente. Instale o grupo de requirements correspondente.", file=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
