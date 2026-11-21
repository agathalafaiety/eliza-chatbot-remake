# Publicar a demonstração da ELIZA

A demonstração pública roda o Classic com histórico em memória, separado por sessão. Ela instala apenas Streamlit e usa o motor de regras em português brasileiro. Gemini, ChromaDB e SQLite ficam na aplicação local.

## Testar localmente

Na raiz do projeto, execute o mesmo arquivo que será usado na hospedagem.

```powershell
.\.venv\Scripts\python.exe -m streamlit run demo/streamlit_app.py --server.address=127.0.0.1
```

Envie uma mensagem e confira a resposta. Abra outra janela anônima e verifique que ela começa com o histórico vazio. **Nova conversa** limpa a sessão atual.

## Configurar no Streamlit Community Cloud

Após conectar o GitHub ao workspace no [Streamlit Community Cloud](https://share.streamlit.io/), crie o aplicativo com esses dados.

| Campo | Valor |
| --- | --- |
| Repositório | `agathalafaiety/eliza-chatbot-remake` |
| Branch | A branch publicada que contém a demonstração |
| Caminho do aplicativo | `demo/streamlit_app.py` |
| Python | `3.12` |

Deixe **Secrets** vazio. Use o endereço `streamlit.app` atribuído pelo serviço e teste-o em uma janela anônima antes de compartilhá-lo. [Guia de publicação do Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
