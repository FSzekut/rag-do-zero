# SPEC — Parte 1: chat de IA publicado, com esteira de CI/CD

> Documento escrito **antes** do código. Se algo aqui estiver errado, corrija **este
> arquivo** primeiro e só depois a implementação.
>
> Origem: [`ideia_1.md`](ideia_1.md) · Data: 24/09/2026 · Status: aguardando aprovação

---

## 1. Objetivo, público e escopo

### Objetivo

Colocar no ar um chat de IA que qualquer pessoa abra por um link, e construir em volta
dele a **esteira automática de publicação**: eu salvo uma alteração no GitHub, um robô
confere se está tudo certo e, se estiver, o site se atualiza sozinho. Se eu errar, a
publicação é barrada e a versão anterior continua no ar.

O chat é a desculpa; **a esteira é o que estou aprendendo**.

### Público

1. **Quem usa**: estudantes com dúvidas de engenharia de dados e IA. Abrem o link,
   perguntam, recebem explicação didática. Não instalam nada, não fazem login.
2. **Quem mantém**: eu. Preciso mudar nome, cores, logo, modelo e instruções
   **editando um arquivo pelo site do GitHub**, sem abrir terminal.

### Entra nesta parte 1

- Interface de chat em português, publicada no Hugging Face Spaces
- Três provedores de IA aceitos (OpenRouter, Anthropic, OpenAI) com troca automática
- Um arquivo de configuração que controla textos, cores, logo, modelos e limites
- Portão de qualidade automático: lint, testes, validação da configuração e varredura
  de segredos
- Publicação automática a cada alteração aprovada na branch `main`

### Fica para a parte 2

- Base de conhecimento com documentos próprios (o RAG: carga, chunking, embeddings,
  busca vetorial). Os esqueletos que já existiam em `src/rag/` saem do caminho agora e
  voltam nessa etapa — nada se perde, tudo fica no histórico do git.
- Citação de fontes nas respostas

### Fica para a parte 3

- Site próprio, com domínio e visual feito do zero
- Login de usuários e histórico de conversas salvo

### Fora de escopo, sem data

Pagamento, painel administrativo, múltiplos idiomas, moderação de conteúdo.

---

## 2. Stack escolhida e restrições do Hugging Face Spaces

### As peças

| Peça | Escolha | Por que esta |
|---|---|---|
| Interface | **Gradio** | é o formato nativo do Spaces; chat com botões de exemplo sai pronto |
| Configuração | **YAML** (`config.yaml`) | aceita comentários e é o mais fácil de editar pelo site do GitHub |
| Linguagem | **Python 3.12** | é a versão que o próprio Space declara no `README.md`; o CI usa a mesma |
| Anthropic | SDK oficial **`anthropic`** | exigência do projeto |
| OpenAI | SDK **`openai`** | exigência do projeto |
| OpenRouter | SDK **`openai`** com `base_url = https://openrouter.ai/api/v1` | a API do OpenRouter é compatível com a da OpenAI |
| Testes | **pytest** | já usado nos outros projetos |
| Lint | **ruff** | rápido e já está no `requirements.txt` |
| Esteira | **GitHub Actions** | o CI/CD que estou aprendendo |
| Hospedagem | **Hugging Face Spaces**, CPU básico, grátis | só chamamos API, não rodamos modelo local |

### Os três provedores, com modelos verificados em 24/09/2026

| Ordem | Provedor | Variável da chave | Modelo padrão | Custo |
|---|---|---|---|---|
| 1º | OpenRouter | `OPENROUTER_API_KEY` | `google/gemma-4-31b-it:free` | **zero** |
| 2º | Anthropic | `ANTHROPIC_API_KEY` | `claude-opus-5` | US$ 5 / 25 por milhão de tokens |
| 3º | OpenAI | `OPENAI_API_KEY` | `gpt-6-sol` | US$ 2 / 10 por milhão de tokens |

Os três slugs foram conferidos no catálogo do OpenRouter em 24/09/2026 —
`google/gemma-4-31b-it:free` existe e está com preço zero. Duas ressalvas honestas:

- **"existe no catálogo" não é o mesmo que "respondeu agora".** Modelo gratuito fica
  lotado em horário de pico e devolve erro; é exatamente para isso que existe a troca
  automática. Só dá para confirmar de verdade com a chave em mãos, no primeiro teste.
- O nome do modelo da OpenAI **para uso direto** (`gpt-6-sol`) foi deduzido do slug do
  OpenRouter, tirando o prefixo `openai/`. Confirmar em `platform.openai.com/docs/models`
  antes de depender dele. Como a OpenAI é a terceira da fila, um nome errado aqui não
  derruba o app — aparece como falha do terceiro provedor.

### Restrições do Hugging Face Spaces que moldam o projeto

1. **O disco é apagado a cada reinício.** No plano grátis não existe armazenamento
   permanente. Nada que o app gravar sobrevive. Não é problema na parte 1, mas é a
   razão pela qual a parte 2 vai ter que levar o índice pronto dentro do repositório.
2. **O `README.md` precisa de um cabeçalho especial.** As primeiras linhas do arquivo
   têm que ser um bloco YAML entre `---` declarando `sdk`, `sdk_version` e `app_file`.
   Sem esse bloco o Space nem tenta construir.
3. **O arquivo principal é `app.py` na raiz.** É o que o Space executa.
4. **Publicar é dar `git push`** para `huggingface.co/spaces/FSzekut/professor-eng-dados`,
   autenticado com um token de **escrita**. O token `RAGnaldo` que já existe é de
   **leitura** e não serve para isso.
5. **As chaves ficam nos *Secrets* do Space**, não no repositório. Dentro do app elas
   aparecem como variáveis de ambiente comuns.
6. **CPU básico, 2 vCPU e 16 GB**, sem GPU. Suficiente: o trabalho pesado acontece no
   servidor do provedor de IA.
7. **O Space adormece** depois de um tempo sem visita e acorda na próxima, com alguns
   segundos de espera. Comportamento normal do plano grátis.

---

## 3. Estrutura de arquivos

```text
rag-do-zero/
├── app.py                        # o que o Space executa: monta a interface
├── config.yaml                   # ÚNICO arquivo que eu edito para personalizar
├── requirements.txt              # o que o Space instala para rodar
├── requirements-dev.txt          # o que eu instalo para testar (pytest, ruff)
├── pytest.ini                    # diz ao pytest onde procurar o código
├── .env.example                  # os nomes das três chaves, sem valor nenhum
├── README.md                     # com o cabeçalho YAML do Space
├── SPEC-parte1-cicd-deploy.md    # este documento
├── ideia_1.md                    # a ideia em linguagem simples
├── assets/
│   └── .gitkeep                  # a logo entra aqui quando existir
├── src/
│   └── assistente/
│       ├── __init__.py
│       ├── config.py             # lê e valida o config.yaml
│       ├── provedores.py         # a fila de provedores e a troca automática
│       └── interface.py          # monta a tela a partir do config
├── scripts/
│   └── validar_config.py         # o portão: roda no CI e falha se a config estiver errada
├── tests/
│   ├── test_config.py
│   ├── test_provedores.py
│   └── exemplos/                 # configs de mentira, umas certas e outras erradas
└── .github/
    └── workflows/
        ├── ci.yml                # lint + testes + validação + varredura de segredos
        └── deploy.yml            # publica no Space quando o CI passa na main
```

> **Nome do repositório ≠ nome do Space.** O código mora em
> `github.com/FSzekut/rag-do-zero` e é publicado em
> `huggingface.co/spaces/FSzekut/professor-eng-dados`. São dois remotes do mesmo
> repositório local; nada precisa ter o mesmo nome. O nome `rag-do-zero` passa a fazer
> sentido na parte 2, quando o RAG entrar.

**Por que `src/assistente/` e não tudo no `app.py`:** o que está em `src/` pode ser
testado sem abrir a tela. `app.py` fica sendo só a cola. É essa separação que permite o
portão de testes rodar em segundos, sem chave de API nenhuma.

---

## 4. Contrato do `config.yaml`

Regras gerais:

- Campo **obrigatório** ausente ou vazio → a publicação é barrada, com o nome do campo
  na mensagem de erro.
- Campo **opcional** ausente → vale o padrão da tabela.
- Campo desconhecido → **erro**, não silêncio. Quase sempre é um nome escrito errado.

### 4.1 `assistente`

| Campo | Obrigatório | Valores aceitos | Padrão |
|---|---|---|---|
| `nome` | sim | texto, 1 a 60 caracteres | — |
| `descricao` | sim | texto, 1 a 200 caracteres | — |
| `logo` | não | caminho relativo de arquivo existente (`.png`, `.jpg`, `.svg`), ou vazio | `""` (sem logo) |
| `logo_altura_px` | não | inteiro de 16 a 200 | `64` |

### 4.2 `aparencia`

| Campo | Obrigatório | Valores aceitos | Padrão |
|---|---|---|---|
| `cor_primaria` | sim | cor hexadecimal `#RGB` ou `#RRGGBB` | — |
| `cor_secundaria` | não | cor hexadecimal, ou vazio | `""` (usa só a primária) |
| `tema` | não | `claro` ou `escuro` | `claro` |

### 4.3 `comportamento`

| Campo | Obrigatório | Valores aceitos | Padrão |
|---|---|---|---|
| `papel` | sim | texto, 10 a 2000 caracteres | — |
| `publico` | não | texto até 300 caracteres | `""` |
| `proibicoes` | não | lista de textos, até 10 itens | `[]` |
| `mensagem_boas_vindas` | não | texto até 300 caracteres | `""` |

Os quatro campos são costurados num só texto de instrução enviado ao modelo. O usuário
do chat nunca vê esse texto.

### 4.4 `perguntas_exemplo`

| Campo | Obrigatório | Valores aceitos | Padrão |
|---|---|---|---|
| `perguntas_exemplo` | não | lista de 0 a 6 textos, cada um até 120 caracteres | `[]` |

Viram os botões clicáveis da tela. Lista vazia = nenhum botão.

### 4.5 `limites`

| Campo | Obrigatório | Valores aceitos | Padrão |
|---|---|---|---|
| `tamanho_maximo_resposta` | não | inteiro de 100 a 4000 (em tokens) | `800` |
| `mensagens_por_sessao` | não | inteiro de 1 a 200 | `20` |

`mensagens_por_sessao` é a proteção de custo combinada: passou do limite, a aba precisa
ser recarregada. Não impede abuso determinado — impede a conta surpresa do dia a dia.

### 4.6 `provedores`

Lista **ordenada**. A ordem é a preferência: o primeiro é tentado primeiro.

| Campo | Obrigatório | Valores aceitos | Padrão |
|---|---|---|---|
| `nome` | sim | `openrouter`, `anthropic` ou `openai` | — |
| `modelo` | sim | texto não vazio | — |

Regras: a lista precisa ter pelo menos 1 item; nome repetido é erro; nome fora dos três
é erro.

### 4.7 Exemplo completo e válido

```yaml
assistente:
  nome: "Professor de Engenharia de Dados"
  descricao: "Tire dúvidas de engenharia de dados e IA, explicado passo a passo."
  logo: ""
  logo_altura_px: 64

aparencia:
  cor_primaria: "#1f6feb"
  cor_secundaria: "#0d1117"
  tema: escuro

comportamento:
  papel: |
    Você é um professor de engenharia de dados e inteligência artificial.
    Explique como quem ensina: comece pelo conceito, depois dê um exemplo concreto.
  publico: "Estudantes de pós-graduação, sem experiência prévia na área."
  proibicoes:
    - "Não invente números, fontes ou citações."
    - "Não responda sobre assuntos fora de dados e IA."
  mensagem_boas_vindas: "Olá! Sobre o que você quer conversar hoje?"

perguntas_exemplo:
  - "O que é um data lake e quando ele é melhor que um banco relacional?"
  - "Qual a diferença entre ETL e ELT?"
  - "Como funciona um embedding, na prática?"

limites:
  tamanho_maximo_resposta: 800
  mensagens_por_sessao: 20

provedores:
  - nome: openrouter
    modelo: "google/gemma-4-31b-it:free"
  - nome: anthropic
    modelo: "claude-opus-5"
  - nome: openai
    modelo: "gpt-6-sol"
```

---

## 5. Requisitos funcionais

### Configuração

- **RF1** — O app lê `config.yaml` da raiz ao iniciar e aplica tudo o que está lá: nome,
  descrição, cores, logo, instruções, perguntas de exemplo, limites e provedores.
- **RF2** — Configuração inválida **impede o app de subir**, com mensagem que diz o campo
  e o motivo (ex.: `aparencia.cor_primaria: "azul" não é uma cor hexadecimal`).
- **RF3** — O mesmo validador roda no CI, antes de publicar. Configuração errada = nada é
  publicado; a versão anterior continua no ar.

### Provedores e troca automática

- **RF4** — O app aceita as três chaves: `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, lidas do ambiente.
- **RF5** — Funciona com **qualquer uma sozinha**. Provedor sem chave cadastrada é
  ignorado, mesmo que esteja no `config.yaml`.
- **RF6** — A ordem de tentativa é a ordem da lista `provedores`, filtrada pelos que têm
  chave.
- **RF7** — Se um provedor falha **antes de responder**, o app tenta o próximo sozinho,
  sem o usuário perceber. Contam como falha: chave inválida (401/403), limite atingido
  (429), crédito insuficiente (402), erro do servidor (5xx), tempo esgotado e falha de
  conexão.
- **RF8** — Se **todos** falharem, o chat mostra uma mensagem listando cada provedor e o
  motivo da falha dele, em português.
- **RF9** — Se **nenhuma chave** estiver cadastrada, a tela abre normalmente e a primeira
  resposta explica que falta configurar uma chave nos *Secrets* do Space.
- **RF10** — Anthropic é chamada pelo SDK `anthropic`; OpenAI e OpenRouter pelo SDK
  `openai`, o último com `base_url = https://openrouter.ai/api/v1`.

### Interface

- **RF11** — A tela mostra logo (se houver), nome e descrição no topo, e usa as cores do
  `config.yaml`.
- **RF12** — As perguntas de exemplo aparecem como botões; clicar envia a pergunta.
- **RF13** — Todo texto visível está em português.
- **RF14** — A conversa mantém o histórico da sessão e o envia ao modelo, respeitando o
  limite de `mensagens_por_sessao`. Atingido o limite, o app avisa e para de responder.
- **RF15** — A resposta chega de uma vez, não palavra por palavra. Motivo: "falhou antes
  de responder" vira uma regra simples e testável. Resposta em fluxo fica para depois.

### Segurança

- **RF16** — Nenhuma chave no repositório. As chaves vivem só nos *Secrets* do Space.
- **RF17** — O CI varre os arquivos atrás de padrões de chave (`sk-ant-`, `sk-or-`,
  `sk-`, `hf_`) e **falha** se achar algum.
- **RF18** — Mensagem de erro mostrada ao usuário nunca contém a chave, nem pedaço dela.

---

## 6. Portão de testes

Todos rodam **sem chave de API** e **sem internet**. Chamada de provedor é substituída
por dublê nos testes.

| # | Verificação | Falha quando |
|---|---|---|
| **T1** | `ruff check .` | há erro de lint ou import não usado |
| **T2** | Config de exemplo válida carrega | algum campo válido é rejeitado |
| **T3** | Campo obrigatório ausente é rejeitado | o carregador aceita config sem `nome`, `descricao`, `papel`, `cor_primaria` ou `provedores` |
| **T4** | Valor fora do domínio é rejeitado | aceita cor sem `#`, `logo_altura_px` fora de 16-200, `tema` diferente de claro/escuro |
| **T5** | Campo desconhecido é rejeitado | aceita `cor_primária` (com acento) ou qualquer nome inventado |
| **T6** | Logo inexistente é rejeitada | aceita caminho de arquivo que não existe |
| **T7** | Lista de provedores é validada | aceita lista vazia, nome repetido ou provedor fora dos três |
| **T8** | Só provedores com chave entram na fila | um provedor sem chave é tentado |
| **T9** | Troca automática funciona | com o 1º devolvendo erro 429, a resposta do 2º não chega |
| **T10** | Todos falharem produz relatório | a mensagem final não nomeia cada provedor e seu motivo |
| **T11** | Nenhuma chave cadastrada não quebra o app | levanta exceção em vez de explicar o que falta |
| **T12** | Mensagem de erro não vaza chave | um trecho da chave aparece no texto de erro |
| **T13** | `scripts/validar_config.py` devolve código 0/1 corretamente | sai com 0 numa config quebrada |
| **T14** | Varredura de segredos acusa chave plantada | um arquivo com `sk-ant-` de mentira passa |

---

## 7. Esteira de publicação

### O caminho de uma alteração

```text
eu edito config.yaml pelo site do GitHub
        ↓
push na branch main
        ↓
GitHub Actions — ci.yml
  ruff  →  pytest  →  validar_config.py  →  varredura de segredos
        ↓                                        ↓
     tudo verde                             algo vermelho
        ↓                                        ↓
GitHub Actions — deploy.yml               NADA é publicado
  push para o remote do Space             o Space continua com a versão antiga
        ↓                                 o e-mail do GitHub diz o que quebrou
o Space reconstrói e sobe (1-3 min)
```

### `ci.yml`

Dispara em push e pull request para `main`. Um job só, Python 3.12: instala as
dependências, roda `ruff check .`, `pytest`, `python scripts/validar_config.py
config.yaml` e a varredura de segredos. Nenhum secret é usado — de propósito, para que
um pull request de fora nunca tenha acesso a nada.

### `deploy.yml`

Dispara só em push na `main`, e só roda se o `ci.yml` terminou verde. Usa o secret
`HF_TOKEN` para dar push no remote do Space. Precisa do histórico completo do git
(`fetch-depth: 0`), senão o push é rejeitado.

### O que eu preciso configurar à mão, uma vez

| # | Onde | O que fazer |
|---|---|---|
| 1 | Hugging Face | criar o Space **`FSzekut/professor-eng-dados`**, SDK Gradio, CPU básico, **público** |
| 2 | Hugging Face → *Access Tokens* | criar token **fine-grained com permissão de escrita neste Space**. Não reaproveitar o `RAGnaldo`, que é de leitura |
| 3 | GitHub → *Settings* → *Secrets* → *Actions* | criar o secret `HF_TOKEN` com esse token — ✅ **feito em 24/09/2026, 20:52** |
| 4 | Hugging Face → Space → *Settings* → *Variables and secrets* | criar os secrets das chaves que eu tiver: `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` |
| 5 | OpenRouter | criar conta e gerar a chave (é o provedor gratuito, o mais importante de ter) |

Os passos 1 a 3 são obrigatórios para publicar. O passo 4 pode ter só uma chave — o app
funciona com qualquer uma sozinha.

> ⚠️ O passo 3 está feito, mas **não dá para conferir de fora se o token é de escrita** —
> o GitHub guarda o valor e não mostra a permissão. Se o token gravado for o `RAGnaldo`
> (leitura), a tarefa 7 falha no `git push` com *403 Forbidden*. Conferir na página de
> *Access Tokens* do Hugging Face antes de chegar lá.

---

## 8. Critérios de aceite

- [ ] Abro `huggingface.co/spaces/FSzekut/professor-eng-dados` e converso com o
      assistente; ele responde em português, como professor
- [ ] A tela mostra o nome e a descrição do `config.yaml`, nas cores escolhidas
- [ ] Os botões de pergunta de exemplo aparecem e funcionam
- [ ] Com **só** a chave do OpenRouter cadastrada, o chat responde
- [ ] Tirando a chave do OpenRouter e deixando só outra, o chat continua respondendo
- [ ] Com o primeiro provedor falhando, a resposta vem do segundo sem eu perceber
- [ ] Sem chave nenhuma, a tela abre e explica que falta cadastrar chave
- [ ] Mudo uma cor pelo site do GitHub e, minutos depois, o Space mostra a mudança
- [ ] Escrevo `cor_primaria: azul` de propósito: o CI fica vermelho, **nada é publicado**
      e o Space continua funcionando com a versão anterior
- [ ] Planto uma chave falsa num arquivo: o CI barra a publicação
- [ ] `pytest` passa localmente sem nenhuma chave de API configurada
- [ ] Nenhuma chave aparece em qualquer arquivo do repositório

---

## 9. Ordem de implementação

Uma tarefa por vez. Cada uma termina com um commit que roda e com o seu teste passando.

| Tarefa | O que entrega | Pronto quando |
|---|---|---|
| **1** | Arrumar a casa: tirar os esqueletos da parte 2, `requirements.txt` novo, `README.md` com o cabeçalho do Space, pastas da seção 3 criadas | `git log` mostra o commit e o repositório tem a estrutura da seção 3 |
| **2** | `config.yaml` de exemplo + leitor validado (`src/assistente/config.py`) | T2 a T7 passam |
| **3** | `scripts/validar_config.py`, o portão em forma de comando | T13 passa |
| **4** | Camada de provedores com troca automática (`src/assistente/provedores.py`) | T8 a T12 passam |
| **5** | `app.py` + `src/assistente/interface.py`, a tela montada pelo config | roda local em `http://localhost:7860` e responde |
| **6** | `.github/workflows/ci.yml` com os quatro passos do portão | T1 e T14 passam, e o CI fica verde no GitHub |
| **7** | `.github/workflows/deploy.yml` e a publicação no Space | o link abre e responde |
| **8** | Conferir os critérios de aceite da seção 8, um a um | todos marcados |

As tarefas 1 a 5 são locais e não dependem de nenhuma conta. A configuração manual da
seção 7 precisa estar pronta antes da tarefa 7.

---

## 10. Erros comuns e como resolver

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Space fica em **"Build error"** logo de cara | falta o cabeçalho YAML no `README.md`, ou `sdk_version` incompatível | conferir as primeiras linhas do `README.md`; a versão do `sdk_version` tem que existir |
| Space sobe mas mostra **"No application file"** | o arquivo principal não é `app.py`, ou `app_file` no cabeçalho aponta para outro lugar | manter `app.py` na raiz |
| `git push` para o Space é **rejeitado** | token de leitura, ou histórico raso | usar o token de escrita; `fetch-depth: 0` no workflow |
| O chat responde **"falta cadastrar chave"** mesmo com a chave criada | o secret está no repositório do GitHub, e não no Space; ou o nome está diferente | o nome tem que ser exatamente `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, dentro do Space |
| O modelo gratuito devolve **429** o tempo todo | modelo `:free` lotado | é o comportamento esperado; a troca automática cobre. Se incomodar, trocar o slug no `config.yaml` |
| O CI falha com **erro de YAML** e uma linha estranha | tabulação no lugar de espaço | YAML não aceita tab; usar dois espaços |
| Erro **"campo desconhecido: cor_primária"** | acento no nome do campo | os nomes dos campos são sem acento; os textos dentro deles, com acento |
| O deploy passa mas o Space **não muda** | o push foi para o GitHub e não para o Space, ou o Space está dormindo | conferir o log do `deploy.yml`; abrir o Space e esperar alguns segundos |
| A logo não aparece | caminho errado, ou arquivo não commitado | o caminho é relativo à raiz, ex.: `assets/logo.png` |
| O build do Space demora demais ou estoura memória | dependência pesada entrando sem necessidade | na parte 1 nada de IA local entra no `requirements.txt`: só `gradio`, `pyyaml`, `anthropic`, `openai` |
| O CI passa no meu computador e falha no GitHub | versão diferente de Python, ou arquivo não commitado | o CI usa Python 3.12; conferir `git status` antes de concluir que "funciona aqui" |

---

## Registro de decisões

| Data | Decisão | Motivo |
|---|---|---|
| 24/09/2026 | Repositório mantém o nome `rag-do-zero`, e o Space chama `professor-eng-dados` | decisão do Fernando; nomes diferentes não atrapalham em nada — o git não liga, e a parte 2 traz o RAG que justifica o nome |
| 24/09/2026 | Gradio em vez de Streamlit | nativo do Spaces, chat e botões de exemplo prontos |
| 24/09/2026 | YAML em vez de JSON | aceita comentário e perdoa mais na edição pelo navegador |
| 24/09/2026 | Resposta de uma vez, sem fluxo palavra a palavra | torna "falhou antes de responder" uma regra simples e testável |
| 24/09/2026 | Actions dando push no Space, em vez da sincronização automática do HF | é o push que permite barrar a publicação quando a configuração está errada |
| 24/09/2026 | Python 3.12, não 3.11 | é o que o Space já declarou no `README.md`; igualar evita o clássico "funciona aqui e falha lá" |
| 24/09/2026 | `requirements.txt` só com o que roda, e `requirements-dev.txt` com pytest e ruff | o Space não precisa instalar ferramenta de teste; build mais leve e rápido |
| 24/09/2026 | Limite de mensagens por sessão | link público com as minhas chaves; o gratuito em primeiro lugar e o limite cobrem o uso normal |
