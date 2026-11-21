"""Valida e executa o notebook inicial sem salvar suas saídas no repositório."""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks" / "01_ambiente.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    print("Estrutura do notebook: OK")
    if arguments.execute:
        # Usa o kernel Python disponível no ambiente que executa este comando.
        # Não registra kernels globais nem salva dados/saídas no arquivo original.
        NotebookClient(
            notebook,
            timeout=120,
            kernel_name="python3",
            resources={"metadata": {"path": str(root)}},
        ).execute()
        code_cells = sum(cell.cell_type == "code" for cell in notebook.cells)
        print(f"Execução do notebook: {code_cells} células de código OK")


if __name__ == "__main__":
    main()
