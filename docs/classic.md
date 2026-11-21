# ELIZA Classic

Classic é uma simulação conversacional inspirada na abordagem DOCTOR da ELIZA histórica. As regras são autorais; não representam uma reprodução integral do script original. O mecanismo não entende sentimentos como uma pessoa e não é profissional de saúde.

## Uso

```python
from eliza import ClassicEliza

bot = ClassicEliza(history_limit=20)
print(bot.welcome_message)
reply = bot.reply("Estou preocupado com meu futuro.")
print(reply.text)  # O que preocupa você em relação a seu futuro?
print(reply.rule_id)  # worried
print(reply.fragment)  # seu futuro
print(bot.respond("Tenho medo de fracassar."))
print(bot.respond("Hmm."))  # referência textual ao último tema capturado
bot.reset()
```

O projeto usa somente português brasileiro. Basta criar `ClassicEliza()`; os parâmetros `pt-BR` e `pt` continuam aceitos como aliases explícitos. Outros idiomas de configuração são rejeitados. `respond()` retorna somente texto. `reply()` acrescenta os metadados da regra, úteis nos exemplos do notebook. `history` retorna os turnos recentes como tupla de objetos imutáveis.

## Como uma resposta é selecionada

1. Valida mensagem e tamanho; normaliza espaços, Unicode e apóstrofos.
2. Compara com a última entrada para reconhecer repetição imediata.
3. Percorre regras na ordem de prioridade, usando expressões regulares sem diferenciar maiúsculas e minúsculas.
4. Quando existe fragmento, aplica reflexões em uma passagem, com expressões maiores antes de palavras individuais. Preserva acentos e não substitui partes internas de outras palavras.
5. Escolhe a próxima resposta daquela regra em rotação fixa. A mesma sequência em uma sessão nova produz as mesmas respostas.
6. Algumas regras atualizam o último tema textual. Quando nenhuma regra corresponde, alterna perguntas genéricas e referência ao último tema disponível.

As regras incluem apresentação, despedida, identidade, negação simples, preocupações, medo, sentimentos, dificuldades, necessidades, desejos, estado, família, sonhos, motivos, generalizações, computadores, afirmações, negativas e perguntas. As regras específicas têm prioridade sobre estado genérico e palavras isoladas. Identidade esclarece que ELIZA é um programa. O último tema não é recuperado por semelhança semântica.

## Estado e limites

- Mensagem: até 4000 caracteres antes da normalização; vazios e entradas sem conteúdo, como `...`, são rejeitados.
- Histórico: últimos 20 turnos por padrão; configurável de 1 a 1000.
- Tema: até 200 caracteres; substituído por novos fragmentos de regras que usam memória.
- Rotação: contador limitado à quantidade de respostas de cada regra.
- `reset()`: limpa histórico, tema, repetição e contadores.
- Sem arquivos de histórico, logs de mensagens, rede, APIs ou dependências de terceiros no mecanismo.

Uma instância deve pertencer a uma conversa; não compartilhe a mesma instância entre usuários. Não há seleção ou detecção de outros idiomas. Regras são heurísticas: podem deixar passar sinônimos, interpretar mal frases com negação complexa ou produzir construções gramaticais pouco naturais. Capturas param no fim da primeira oração reconhecida; mensagens com vários assuntos não são analisadas semanticamente.

## Acompanhar e testar

Abra `notebooks/01_ambiente.ipynb` no VS Code, selecione o kernel `.venv` e execute em ordem. As seções Classic mostram português, transformações, respostas alternativas, repetição e memória. A seção **Converse com a ELIZA** permite editar `minha_mensagem` a cada interação.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe tools/validate_notebook.py --execute
```

O teste offline inicia um processo Python isolado, desativa `site-packages`, retira as variáveis de chave Google e bloqueia criação de sockets. Ele conversa em português e verifica que pacotes de interface, persistência e IA não são importados. Isso valida a independência do mecanismo das dependências instaladas no projeto.

Registro da etapa inicial do Classic, antes da camada de persistência, no Windows com Python 3.12.14 (os resultados atuais da suíte completa estão no [guia de persistência](persistence.md)):

| Comando/verificação | Resultado observado |
|---|---|
| `python -m pytest -q` | 86 testes aprovados para a versão somente em português |
| `python -m ruff check .` | Sem ocorrências |
| `python -m ruff format --check .` | Arquivos formatados |
| `python tools/validate_notebook.py --execute` | Formato válido e dez células de código executadas |
| `python -m pip check` | Nenhum conflito declarado |

Foram adicionados `eliza/__init__.py`, `classic.py`, `patterns.py`, `reflections.py`, `personality.py`, `tests/test_classic.py` e `tests/test_reflections.py`. O notebook, README, arquitetura, guia de notebooks e workflow de qualidade foram atualizados. Nenhuma dependência nova foi necessária para Classic.

A execução automatizada do notebook não altera o arquivo `.ipynb` original nem salva suas saídas. Ao usar o VS Code manualmente, salve o notebook sem mensagens pessoais antes de versioná-lo. A camada `ConversationMemory` oferece [persistência e retomada de conversas](persistence.md). A interface Streamlit oferece o Classic e o modo opcional com Gemini. [Instruções de uso](../README.md)
