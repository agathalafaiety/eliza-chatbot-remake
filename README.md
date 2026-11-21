# Eliza Chatbot Remake

ELIZA Classic em português brasileiro, com chat local no Streamlit, histórico em SQLite e exemplos no Jupyter. A recriação é inspirada no roteiro DOCTOR e usa reconhecimento de padrões, transformação de pronomes e perguntas reflexivas. ELIZA é uma simulação conversacional.

> **Você:** Estou preocupado com meu futuro.
>
> **ELIZA:** O que preocupa você em relação a seu futuro?

O chat funciona offline e permite criar, retomar e excluir conversas. Ao retomar uma conversa, o Classic recupera o contexto a partir das mensagens salvas.

## Começar no Windows

Abra a pasta do projeto no VS Code. Use Python 3.11 ou superior e as extensões Python e Jupyter. Execute os comandos abaixo no PowerShell, na raiz do repositório.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Se `python` abrir a Microsoft Store, use o caminho completo de uma instalação Python funcional para criar `.venv`.

O Streamlit abre o chat no navegador em [127.0.0.1:8501](http://127.0.0.1:8501). Na barra lateral, clique em **Nova conversa** para começar, use **Retomar conversa** para abrir um histórico ou selecione **Excluir conversa** e confirme a exclusão.

As conversas são armazenadas por padrão em `data/eliza.db`. Para escolher outro arquivo, copie `.env.example` para `.env` e ajuste `ELIZA_DATABASE_URL`. [Guia de persistência](docs/persistence.md)

## Acompanhar no Jupyter

Instale `requirements-dev.txt` na mesma `.venv` para adicionar Jupyter, pytest e Ruff.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

1. Abra [o notebook de acompanhamento](notebooks/01_ambiente.ipynb).
2. Em **Select Kernel → Python Environments**, selecione `.venv\Scripts\python.exe`.
3. Clique em **Run All** para executar os exemplos.
4. Em **Converse com a ELIZA**, edite `minha_mensagem` e execute a célula a cada interação.

A conversa editável fica na memória do kernel. Em **Histórico de conversas**, o notebook usa dados fictícios e um arquivo temporário para demonstrar como salvar, reabrir, continuar e excluir uma conversa. [Guia do notebook](docs/notebooks.md)

## Usar o Classic em Python

```python
from eliza import ClassicEliza

eliza = ClassicEliza()
print(eliza.respond("Estou preocupado com meu futuro."))
# O que preocupa você em relação a seu futuro?
```

Cada instância mantém o contexto de uma conversa. Use `reply()` para consultar a regra que gerou a resposta e `reset()` para reiniciar a sessão. [Guia do Classic](docs/classic.md)

## Estrutura do projeto

| Pasta | Responsabilidade |
| --- | --- |
| `ui/` | Chat e gerenciamento de conversas no Streamlit, iniciados por `app.py` |
| `eliza/` | Classic, regras, reflexões, configuração e retomada de conversas |
| `database/` | Modelos SQLAlchemy e operações do histórico SQLite |
| `notebooks/` | Exemplos para Jupyter local |
| `tests/` | Testes do Classic, da configuração e da persistência |
| `tools/` | Verificação do ambiente e execução automatizada do notebook |
| `docs/` | Arquitetura e guias de uso |

Google AI e ChromaDB estão no roteiro. Seus arquivos de dependências são opcionais para quem for experimentar essas integrações. [Arquitetura e próximas etapas](docs/architecture.md)

## Verificar alterações

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe tools/validate_notebook.py --execute
```

Os testes de interface usam o AppTest do Streamlit e um banco SQLite temporário. O workflow de qualidade executa as verificações em Windows e Linux com Python 3.11 e 3.12. [GitHub Actions](.github/workflows/quality.yml)
