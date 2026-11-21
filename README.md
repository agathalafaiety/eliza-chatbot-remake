# Eliza Chatbot Remake

## A ELIZA original

A ELIZA foi um dos primeiros programas de conversação por texto. Joseph Weizenbaum a desenvolveu no MIT e apresentou o trabalho em 1966. O nome veio de Eliza Doolittle, personagem da peça *Pigmalião*, de George Bernard Shaw. [Artigo original](https://doi.org/10.1145/365153.365168)

Seu roteiro **DOCTOR** imitava o estilo de uma conversa terapêutica usando palavras-chave e regras para reformular trechos das mensagens em perguntas. A impressão de que o programa compreendia o interlocutor ficou conhecida como **efeito ELIZA**. [Contexto histórico](https://www.weizenbaum-institut.de/media/Publikationen/Weizenbaum_Journal/CfP_Celebrating_ELIZA.pdf)

## Sobre este projeto

Esta é uma recriação educacional em português brasileiro, com regras próprias inspiradas no DOCTOR. O chat funciona offline no **Streamlit** e usa **SQLite** para salvar, retomar e excluir conversas.

> **Você:** Estou preocupado com meu futuro.
>
> **ELIZA:** O que preocupa você em relação a seu futuro?

## Como executar no Windows

Com Python 3.11 ou superior, execute os comandos abaixo no PowerShell, na raiz do repositório.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Com o Streamlit rodando no seu computador, abra o [chat local](http://127.0.0.1:8501) e clique em **Nova conversa**.

O histórico fica em `data/eliza.db`. [Configuração do banco](docs/persistence.md)

## Modo IA com Gemini

Instale o SDK na mesma `.venv`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ai.txt
```

Crie um arquivo `.env` local a partir de `.env.example` e preencha `GEMINI_API_KEY`. Reinicie o Streamlit e selecione **IA · Gemini** ao criar uma conversa. O modelo padrão é `gemini-3.5-flash-lite` e pode ser alterado em `GEMINI_MODEL`.

O modo IA envia ao Gemini a mensagem atual e até dez turnos recentes da conversa. O Classic continua disponível offline. [Guia da API Gemini](https://ai.google.dev/gemini-api/docs/api-key)

### Memória semântica opcional

Para recuperar trechos antigos da mesma conversa, instale `requirements-memory.txt` na `.venv` e defina `ELIZA_ENABLE_SEMANTIC_MEMORY=true` no `.env`. Os trechos são enviados ao Gemini para gerar embeddings. O ChromaDB guarda os vetores em `data/chroma` e o SQLite continua guardando as mensagens. [Detalhes da arquitetura](docs/architecture.md#memória-semântica)

## Acompanhar no Jupyter

Instale as dependências de desenvolvimento na mesma `.venv`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

No VS Code, abra o [notebook de acompanhamento](notebooks/01_ambiente.ipynb), selecione o kernel `.venv` e clique em **Run All** para ver as regras do Classic e os exemplos de persistência.

## Estrutura do projeto

```text
eliza-chatbot-remake/
├── app.py       # Entrada do Streamlit
├── ui/          # Chat e barra lateral
├── eliza/       # Regras do Classic, configuração e memória
├── database/    # Modelos e repositório SQLite
├── notebooks/   # Exemplos no Jupyter
├── tests/       # Testes do Classic, do banco e da interface
├── tools/       # Verificação do ambiente e do notebook
└── docs/        # Arquitetura e guias de uso
```
