# Arquitetura

O projeto atende em português brasileiro. `app.py` inicia a interface Streamlit. O notebook permite explorar as regras e o histórico no Jupyter local.

## Camadas atuais

| Camada | Responsabilidade |
| --- | --- |
| `app.py`, `ui/` | Abrem o repositório, exibem o chat e gerenciam a conversa selecionada |
| `eliza/classic.py` | Aplica as regras de conversa e mantém o estado de uma sessão usando a biblioteca padrão do Python |
| `eliza/patterns.py`, `reflections.py`, `personality.py` | Definem padrões, substituições de pronomes e textos da simulação |
| `eliza/memory.py` | Reconstrói uma sessão Classic a partir do histórico e coordena o salvamento de cada turno |
| `database/models.py`, `repository.py` | Definem o esquema e as operações de armazenamento em SQLite com SQLAlchemy |
| `eliza/config.py` | Valida a configuração do banco com Pydantic e lê o ambiente e o arquivo `.env` |
| `notebooks/01_ambiente.ipynb` | Mostra o Classic e o ciclo de vida de uma conversa usando dados fictícios |

Para conversar em memória, o notebook chama `ClassicEliza` diretamente. Para salvar uma interação, chama `ConversationMemory.send()` com o identificador da conversa. O serviço lê o histórico pelo repositório, reconstrói o estado do Classic e grava a mensagem e a resposta juntas.

No Streamlit, `st.session_state` guarda a seleção e a confirmação de exclusão. A cada execução a interface lê o histórico do SQLite e encaminha novos envios ao mesmo serviço usado pelo notebook. Cada execução tem seu próprio escopo de repositório. A interface requer um arquivo SQLite para preservar conversas entre execuções.

## Regras e estado da conversa

Classic normaliza a entrada, verifica repetições e busca padrões em ordem de prioridade. A resposta selecionada pode incorporar um fragmento da mensagem com os pronomes ajustados. Cada instância mantém seus próprios contadores de respostas, último tema e os últimos 20 turnos por padrão. [Detalhes do Classic](classic.md)

## Histórico e integridade

SQLite guarda conversas e mensagens em duas tabelas ligadas por uma chave estrangeira. Cada conversa tem um identificador UUID, título, modo, idioma e datas UTC. O repositório lê metadados e mensagens na mesma transação e retorna registros imutáveis. Excluir uma conversa remove suas mensagens em cascata.

Cada par de mensagens corresponde a uma revisão da conversa. A gravação inclui a revisão esperada na atualização e salva o par na mesma transação. Em caso de conflito, o chamador pode recarregar o histórico antes de repetir a operação.

Ao retomar o Classic, o serviço reproduz as entradas anteriores para recompor a rotação de respostas, as repetições e o último tema. Esse trabalho cresce com a quantidade de turnos. Se as regras atuais produzirem respostas diferentes, o histórico continua disponível para leitura e o serviço interrompe a retomada. [API e limites do banco](persistence.md)

## Próximas etapas

1. **Google AI.** Um adaptador opcional recebe o contexto recente dentro de um limite e trata falhas do provedor. O Classic segue disponível offline.
2. **ChromaDB.** Um índice opcional recupera trechos relevantes para o modo AI. SQLite será a fonte do histórico e permitirá reconstruir o índice. Quando a integração existir, a exclusão também deverá remover as entradas correspondentes do índice.
3. **Implantação.** Validar os modos integrados e documentar o ambiente de produção.
