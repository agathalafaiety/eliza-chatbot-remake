# Eliza Chatbot Remake

## O que foi a ELIZA?

A ELIZA foi um dos primeiros programas de conversação por texto. Joseph Weizenbaum a desenvolveu no MIT, na década de 1960, para investigar a comunicação em linguagem natural entre pessoas e computadores. Em 1966, ele descreveu o programa na revista *Communications of the ACM*. O nome veio de Eliza Doolittle, personagem da peça *Pigmalião*, de George Bernard Shaw. [Artigo original de Joseph Weizenbaum](https://doi.org/10.1145/365153.365168)

O programa podia executar roteiros diferentes. Um deles, **DOCTOR**, imitava o estilo de conversa de um psicoterapeuta da abordagem centrada na pessoa. A ELIZA procurava palavras-chave, identificava trechos da mensagem e os reorganizava em respostas previstas pelo roteiro. Reformular uma frase como pergunta era uma forma de manter o diálogo. [Descrição do mecanismo e da simulação no artigo original](https://courses.cs.umbc.edu/undergraduate/331/papers/eliza.january1966.html)

Um aspecto marcante do trabalho é que essas regras podiam criar a impressão de que o programa compreendia o interlocutor. Essa tendência de atribuir compreensão a um programa a partir de suas respostas ficou conhecida como **efeito ELIZA**. [Contexto histórico do Instituto Weizenbaum](https://www.weizenbaum-institut.de/media/Publikationen/Weizenbaum_Journal/CfP_Celebrating_ELIZA.pdf)

## Sobre este projeto

O **Eliza Chatbot Remake** é uma releitura educacional em português brasileiro, com regras próprias inspiradas no DOCTOR. O modo Classic usa expressões regulares, transformação de pronomes e perguntas reflexivas para simular uma conversa. O exemplo abaixo é uma resposta produzida pelo projeto.

> **Você:** Estou preocupado com meu futuro.
>
> **ELIZA:** O que preocupa você em relação a seu futuro?

O chat local roda no **Streamlit** e funciona offline. O histórico em **SQLite** permite criar, retomar e excluir conversas. Ao reabrir uma conversa, o Classic recupera o contexto a partir das mensagens salvas. No **Jupyter**, você pode acompanhar as regras acionadas e experimentar o fluxo de persistência com dados fictícios.

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
