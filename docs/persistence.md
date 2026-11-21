# Conversas persistentes com SQLite

O histórico completo é armazenado em um arquivo SQLite por SQLAlchemy. O serviço de memória conecta esse histórico ao mecanismo Classic, preservando português brasileiro e funcionamento sem API. Não foram adicionadas dependências nesta etapa.

## Banco local

```python
from database import ConversationRepository
from eliza.memory import ConversationMemory

with ConversationRepository.from_settings() as repository:
    conversation = repository.create_conversation("Meu futuro")
    memory = ConversationMemory(repository)
    turn = memory.send(conversation.id, "Estou preocupado com meu futuro.")
    print(turn.assistant.content)
    conversation_id = conversation.id

# Pode ocorrer em outra execução do programa.
with ConversationRepository.from_settings() as repository:
    saved = repository.get_history(conversation_id)
    for message in saved.messages:
        print(message.role, message.content, message.created_at.isoformat())
    turn = ConversationMemory(repository).send(conversation_id, "Ainda penso nisso.")
    print(turn.assistant.content)
```

O arquivo padrão é `data/eliza.db`. A pasta e as tabelas são criadas quando o repositório é aberto. Caminhos relativos em `ELIZA_DATABASE_URL` são resolvidos a partir da raiz do projeto, sem depender da pasta de execução do notebook.

Para configurar outro arquivo, copie `.env.example` para `.env` e ajuste:

```dotenv
ELIZA_DATABASE_URL=sqlite:///data/minhas-conversas.db
```

A variável no ambiente tem precedência sobre `.env`. `Settings` valida a configuração com Pydantic e rejeita bancos de outros tipos, credenciais e parâmetros de conexão nesta etapa. As configurações não alteram `os.environ`. Para escolher um caminho diretamente:

```python
from pathlib import Path

with ConversationRepository(Path("data") / "experimento.db") as repository:
    print(repository.list_conversations())
```

Nesse último caso, um `Path` relativo parte da pasta atual, como qualquer caminho Python; use `from_settings()` para a convenção ancorada na raiz. `:memory:` é aceito para experimentos sequenciais e não persiste após fechar o repositório.

## API

| Operação | Comportamento |
|---|---|
| `create_conversation(title, mode="classic")` | Retorna metadados imutáveis com UUID, título, modo, `pt-BR`, datas e revisão zero |
| `list_conversations(limit=50, offset=0)` | Lista metadados por última atualização, com desempate por UUID; limite de 1 a 1000 |
| `get_conversation(id)` | Retorna metadados ou `None` quando ausente |
| `get_history(id)` | Retorna metadados e todas as mensagens ordenadas, no mesmo snapshot; ausente gera erro |
| `ConversationMemory(repository).send(id, message)` | Reconstrói Classic, gera resposta e salva o par integralmente |
| `ConversationMemory(repository).restore_classic(id)` | Devolve uma instância reconstruída para inspeção; chamadas diretas a ela não são salvas |
| `append_turn(id, user, assistant, expected_revision=..., rule_id=...)` | API de armazenamento do par para adaptadores; exige revisão esperada |
| `delete_conversation(id)` | Remove a conversa e suas mensagens, retornando `True`; retorna `False` se já não existe |
| `close()` / `with` | Libera as conexões; abra outra instância para voltar a usar o arquivo |

O título aceita de 1 a 120 caracteres depois de retirar espaços externos. Mensagens vazias são rejeitadas. O serviço Classic aplica o limite de 4000 caracteres de entrada antes de gravar. As mensagens mantêm conteúdo, papel, posição, UUID, data UTC e a regra da resposta quando disponível.

O modo `ai` pode ser registrado como metadado no repositório, mas o serviço atual recusa gerar respostas para esse modo. Nenhum provedor AI é chamado automaticamente.

## Transações e retomada

A revisão conta turnos completos. Cada turno inclui uma mensagem `user` e uma `assistant`, com posições consecutivas. A atualização da revisão e a inserção das duas mensagens pertencem à mesma transação. Se qualquer inserção falhar, revisão, datas e mensagens são desfeitas juntas.

O serviço lê o histórico, reconstrói uma instância Classic e grava usando a revisão que leu. Uma alteração concorrente provoca `ConversationConflictError`; recarregue o histórico antes de repetir a ação. O serviço não avança uma sessão compartilhada em memória quando a gravação falha. SQLite usa WAL em arquivos e transações explícitas, incluindo as leituras do histórico.

O replay percorre **todas** as entradas anteriores para reconstruir contadores de alternativas, repetição e último tema. O histórico curto do mecanismo continua limitado a 20 turnos, mas o banco guarda todas as mensagens. A retomada é linear no tamanho do histórico; uma otimização futura poderá usar snapshots versionados.

As respostas antigas não são regravadas durante o replay. Se o histórico estiver incompleto, fora de ordem ou suas respostas não corresponderem às regras Classic atuais, o serviço levanta `HistoryMismatchError`. O histórico permanece disponível para consulta e exclusão. Essa verificação evita continuar silenciosamente uma conversa com um estado diferente após mudanças nas regras. Alterações de esquema e migrações entre versões ainda não foram implementadas; abrir o banco cria tabelas ausentes, sem recriar bancos existentes.

As configurações de chaves estrangeiras e de transação seguem a [documentação SQLite do SQLAlchemy](https://docs.sqlalchemy.org/en/21/dialects/sqlite.html); os escopos transacionais usam os [contextos de sessão do SQLAlchemy](https://docs.sqlalchemy.org/en/21/orm/session_transaction.html).

## Excluir uma conversa escolhida

```python
with ConversationRepository.from_settings() as repository:
    conversations = repository.list_conversations()
    # Escolha um identificador da lista antes de excluir.
    # removed = repository.delete_conversation(chosen_id)
```

As mensagens são removidas pela chave estrangeira `ON DELETE CASCADE`, ativa em cada conexão do repositório. Conversas diferentes permanecem intactas. A exclusão não remove o arquivo do banco inteiro. Não há índice ChromaDB de conversas implementado nesta etapa.

Erros de banco são expostos como `StorageError`, `ConversationNotFoundError` ou `ConversationConflictError`, sem conteúdos das mensagens, SQL completo ou caminhos sensíveis nos logs do repositório. Dados locais, bancos e arquivos WAL/SHM estão fora do Git por `.gitignore`.

## Notebook e validação

Abra `notebooks/01_ambiente.ipynb` no VS Code, escolha `.venv`, reinicie o kernel se ele já estava aberto e execute em ordem. A seção **Histórico de conversas** cria uma conversa fictícia, salva interações, fecha/reabre o arquivo, continua com o tema anterior, lista duas conversas e exclui uma delas. A pasta temporária é removida ao concluir. **Run All** não usa o banco permanente em `data/`.

Comandos de validação local:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe tools/validate_notebook.py --execute
```

Os testes cobrem reabertura de arquivo, Unicode, ordem e UTC, paginação, isolamento de conversas, exclusão em cascata, rejeição de órfãos, parâmetros SQL, rollback de uma falha real por trigger, concorrência com revisões, leitura consistente durante outra gravação e retomada Classic além de sua janela de sessão. As verificações usam o ambiente local e não fazem chamadas à API Google. A execução remota do workflow precisa ser verificada separadamente.

Resultados locais desta etapa no Windows, com Python 3.12.14:

| Verificação executada | Resultado |
|---|---|
| `python -m pytest -q` | 139 testes aprovados, incluindo Classic, configuração, banco e memória |
| `python -m ruff check .` | Sem ocorrências |
| `python -m ruff format --check .` | Arquivos formatados |
| `python tools/validate_notebook.py --execute` | Formato válido e 16 células de código executadas |

Foram adicionados os três módulos de `database`, `eliza/config.py`, `eliza/memory.py` e testes para configuração, banco e memória. O notebook, os guias, `.env.example` e o nome da etapa pytest no workflow foram atualizados. O mecanismo Classic e suas regras não foram alterados. Nenhum banco permanente foi aberto ou populado pela validação; os testes e exemplos usam arquivos temporários.
