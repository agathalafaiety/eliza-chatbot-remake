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

O modo é definido na criação da conversa. No modo IA, `eliza/ai.py` usa a API Gemini com instruções em português brasileiro. A requisição inclui a mensagem atual e até dez turnos anteriores completos, limitados a 12.000 caracteres de histórico. O adaptador limita a saída a 512 tokens e configura raciocínio mínimo para Gemini 3.5 Flash e Flash-Lite. O histórico completo fica no SQLite. A geração ocorre antes da gravação e o turno só é salvo após uma resposta com texto e uma verificação da revisão. [Referência da API Gemini](https://ai.google.dev/api/generate-content)

## Regras e estado da conversa

Classic normaliza a entrada, verifica repetições e busca padrões em ordem de prioridade. A resposta selecionada pode incorporar um fragmento da mensagem com os pronomes ajustados. Cada instância mantém seus próprios contadores de respostas, último tema e os últimos 20 turnos por padrão. [Detalhes do Classic](classic.md)

## Histórico e integridade

SQLite guarda conversas e mensagens em duas tabelas ligadas por uma chave estrangeira. Cada conversa tem um identificador UUID, título, modo, idioma e datas UTC. O repositório lê metadados e mensagens na mesma transação e retorna registros imutáveis. Excluir uma conversa remove suas mensagens em cascata.

Cada par de mensagens corresponde a uma revisão da conversa. A gravação inclui a revisão esperada na atualização e salva o par na mesma transação. Em caso de conflito, o chamador pode recarregar o histórico antes de repetir a operação.

Ao retomar o Classic, o serviço reproduz as entradas anteriores para recompor a rotação de respostas, as repetições e o último tema. Esse trabalho cresce com a quantidade de turnos. Se as regras atuais produzirem respostas diferentes, o histórico continua disponível para leitura e o serviço interrompe a retomada. [API e limites do banco](persistence.md)

## Próximas etapas

1. **Implantação.** Validar os modos integrados e documentar o ambiente de produção.

## Memória semântica

`eliza/semantic_memory.py` usa um índice ChromaDB por conversa Gemini. O recurso começa desativado. Para ativá-lo, instale `requirements-memory.txt` e defina `ELIZA_ENABLE_SEMANTIC_MEMORY=true` no `.env`. `ELIZA_CHROMA_PATH` permite escolher a pasta local do índice.

O índice guarda identificadores de turnos e vetores. Os textos são consultados no SQLite. Primeiro, o sistema separa os turnos recentes já incluídos no contexto. Depois considera até 100 turnos mais antigos, indexando até 12 turnos faltantes por envio. A busca por distância de cosseno pode trazer até três turnos completos, com limite adicional de 3.600 caracteres. A busca fica restrita à conversa aberta e só utiliza identificadores presentes no histórico.

Para gerar os vetores, o aplicativo envia os trechos antigos e a mensagem atual à API Gemini com o modelo `gemini-embedding-001`. Se o SDK, o índice ou os embeddings ficarem indisponíveis, o Gemini segue com o contexto recente. [Documentação dos embeddings Gemini](https://ai.google.dev/gemini-api/docs/embeddings)

A exclusão pela interface remove primeiro a coleção da conversa, se ela existir na pasta configurada, e depois exclui o histórico SQLite. Uma falha na remoção do índice mantém a conversa disponível para repetir a operação. O ChromaDB roda no mesmo processo da aplicação local. [Documentação do cliente persistente Chroma](https://docs.trychroma.com/reference/python/client)
