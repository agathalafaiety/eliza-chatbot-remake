# Eliza Chatbot Remake

Como um programa de regras simples consegue dar a impressão de que está acompanhando uma conversa? Este projeto revisita essa ideia da ELIZA com uma recriação em português brasileiro, inspirada no roteiro DOCTOR.

> **Você:** Estou preocupado com meu futuro.
>
> **ELIZA:** O que preocupa você em relação a seu futuro?

A regra reconhece a expressão de preocupação, troca “meu” por “seu” e reaproveita o trecho em uma pergunta. No Jupyter, você pode acompanhar qual regra foi acionada a cada resposta. O Classic funciona offline como uma simulação conversacional.

## Decisões de engenharia

- **Respostas rastreáveis.** O Classic aplica regras por prioridade e alterna as respostas em ordem fixa. A mesma sequência de mensagens reproduz a conversa.
- **Histórico consistente.** SQLite guarda a mensagem e a resposta na mesma transação. O controle de revisão detecta quando outra gravação alterou a conversa.
- **Sessões que podem ser retomadas.** Ao reabrir o histórico, o serviço reproduz as entradas anteriores para recuperar a rotação de respostas e o último tema.

O notebook demonstra a conversa e o ciclo completo do histórico. Streamlit, Google AI e ChromaDB fazem parte do [roteiro de desenvolvimento](docs/architecture.md#próximas-etapas).

## Começar no Windows

Abra a pasta do projeto no VS Code. Use Python 3.11 ou superior e as extensões Python e Jupyter. Execute os comandos abaixo no PowerShell, na raiz do repositório.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Se `python` abrir a Microsoft Store, use o caminho completo de uma instalação Python funcional para criar `.venv`.

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

Para persistir o histórico, use `ConversationRepository.from_settings()` e envie mensagens via `ConversationMemory.send()`. O banco padrão é `data/eliza.db`. Para definir outro caminho, copie `.env.example` para `.env` e ajuste `ELIZA_DATABASE_URL`. O Git ignora o banco padrão e o arquivo `.env`. [Guia de persistência e exemplos da API](docs/persistence.md)

## Estrutura do projeto

| Pasta | Responsabilidade |
| --- | --- |
| `eliza/` | Classic, regras, reflexões, configuração e retomada de conversas |
| `database/` | Modelos SQLAlchemy e operações do histórico SQLite |
| `notebooks/` | Exemplos para Jupyter local |
| `tests/` | Testes do Classic, da configuração e da persistência |
| `tools/` | Verificação do ambiente e execução automatizada do notebook |
| `docs/` | Arquitetura e guias de uso |

`requirements-dev.txt` instala a base de `requirements.txt` junto com Jupyter, pytest e Ruff. Os arquivos opcionais `requirements-ai.txt` e `requirements-memory.txt` acrescentam o SDK Google e o ChromaDB, respectivamente. [Arquitetura e próximas etapas](docs/architecture.md)

## Verificar alterações

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe tools/validate_notebook.py --execute
```

O workflow de qualidade executa as verificações em Windows e Linux com Python 3.11 e 3.12. [GitHub Actions](.github/workflows/quality.yml)
