# Acompanhamento com notebooks

## No VS Code

Abra a pasta inteira do projeto e selecione `.venv\Scripts\python.exe` como interpretador Python. Abra `notebooks/01_ambiente.ipynb` e escolha o mesmo ambiente no seletor de kernel, no canto superior direito. O notebook não depende de um kernel registrado globalmente.

A extensão Jupyter do VS Code executa notebooks com `ipykernel`; não é necessário instalar a interface web completa do Jupyter. As células são independentes de uma chave de API. Há exemplos fictícios, uma conversa Classic editável em memória e uma seção de persistência em SQLite.

## Conversar no notebook

1. Use **Run All** para ver os exemplos de português, transformação de pronomes, alternativas e memória curta.
2. Na seção **Converse com a ELIZA**, a primeira célula cria `minha_eliza`.
3. Na célula seguinte, altere `minha_mensagem` e execute com `Shift+Enter`.
4. Repita o passo 3 a cada mensagem. O histórico recente aparece na saída.
5. Para começar outra conversa, execute novamente a célula que cria `minha_eliza` ou chame `minha_eliza.reset()`.

Executar **Run All** reinicia os exemplos e a conversa editável. Reiniciar o kernel apaga todas as sessões. Para carregar mudanças feitas nos módulos `.py`, reinicie o kernel e execute as células novamente.

## Acompanhar a persistência SQLite

A seção **Histórico de conversas** usa as APIs reais do projeto, em um arquivo temporário separado do banco permanente:

1. A célula de importação carrega repositório e serviço de memória.
2. **Criar uma conversa** cria um banco temporário e uma conversa com título, modo, idioma e datas UTC.
3. **Salvar mensagens** envia e salva pares de mensagens usando `ConversationMemory.send()`.
4. **Retomar a conversa** fecha o repositório, abre o mesmo arquivo, recupera o histórico e continua a conversa com o tema anterior.
5. **Listar conversas salvas** cria outra conversa e lista os registros, demonstrando isolamento.
6. **Excluir uma conversa** exclui somente a primeira conversa fictícia, verifica a preservação da segunda e remove os arquivos temporários ao finalizar.

Execute em ordem. Para repetir somente essa demonstração, volte à célula **Criar uma conversa**. O notebook inclui uma receita não executada para usar o banco permanente em `data/eliza.db`; consulte também [o guia de persistência](persistence.md). A conversa editável da seção Classic continua em memória e não é salva automaticamente.

## Limites e dados

- O notebook usa o kernel `.venv` da pasta local do projeto e importa os módulos diretamente desta pasta.
- Os bancos demonstrados no notebook são temporários, com mensagens fictícias. A conversa livre Classic continua somente na memória; a seção de persistência salva explicitamente outras conversas fictícias. O banco permanente usa `data/`, fora do Git, quando você abre `ConversationRepository.from_settings()`.
- Não copie a chave Google para células ou saídas; quando a integração AI for implementada, use o arquivo local `.env`.
- ChromaDB e Google AI serão demonstrados em notebooks próprios quando essas funcionalidades forem implementadas.
- Para conversar no navegador e usar o histórico permanente, inicie o Streamlit conforme o [README](../README.md#como-executar-no-windows).

## Verificação automatizada local

```powershell
.\.venv\Scripts\python.exe tools/validate_notebook.py --execute
```

Esse comando valida o formato e executa todas as células localmente, sem salvar saídas no notebook.
