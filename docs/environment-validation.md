# Validação da preparação do ambiente

Verificação local realizada em 20/11/2026, no Windows, usando o Python 3.12.14 de `.venv`.

## Resultados observados

| Verificação | Resultado |
|---|---|
| `python -m pip check` | Nenhum conflito de dependências declarado |
| `python tools/check_environment.py --notebooks --optional` | Imports, SQLite, ferramentas Jupyter, SDK Google e ChromaDB aprovados |
| SQLite via SQLAlchemy | Gravação em arquivo temporário, fechamento e recuperação após reabertura aprovados |
| ChromaDB | Inclusão, consulta e exclusão aprovadas com vetores artificiais |
| `python tools/validate_notebook.py --execute` | Formato válido e quatro células de código executadas sem erro |
| `python -m ruff check .` | Sem ocorrências |
| `python -m ruff format --check .` | Arquivos formatados |
| Configurações do VS Code e Streamlit | JSON e TOML analisados sem erro |
| `.gitignore` | Ambiente, segredos e bancos locais ignorados; `.env.example` permanece versionável |

Os comandos acima devem usar `.\.venv\Scripts\python.exe` no PowerShell desta pasta. A execução do kernel Jupyter foi autorizada fora da restrição de processos/portas da ferramenta de desenvolvimento, após a execução restrita não concluir. Não foi necessário alterar a política de execução do PowerShell ou registrar um kernel global.

## Versões principais instaladas

- Streamlit 1.67.0
- SQLAlchemy 2.1.9
- SQLite 3.53.4, incluído no interpretador utilizado
- python-dotenv 1.2.4
- Pydantic 2.14.4
- pytest 9.2.0
- Ruff 0.17.6
- ipykernel 7.4.0
- nbformat 5.11.1
- nbclient 0.11.0
- Google Gen AI SDK 3.6.1
- ChromaDB 1.5.9

As versões diretas estão fixadas nos arquivos `requirements*.txt`. Dependências transitivas são resolvidas pelo pip; ainda não existe um lock completo para todas as plataformas.

## Limites desta validação

- O notebook foi executado no kernel Jupyter local da `.venv`.
- Nenhuma chave foi lida, solicitada ou gravada. O SDK Google foi importado sem chamar a API.
- A consulta ChromaDB usou vetores artificiais; ainda não existe avaliação de embeddings em português ou persistência vetorial da aplicação.
- Pytest está instalado, mas ainda não há testes da aplicação. Nenhuma execução de suíte pytest é declarada nesta etapa.
- O workflow GitHub Actions foi preparado, mas não executado no GitHub.
- O chatbot e `app.py` ainda serão implementados; esta etapa não valida uma interface de chat pronta.
- Não houve push ao GitHub.
