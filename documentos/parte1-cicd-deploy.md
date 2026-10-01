# Construindo seu Chat de IA Personalizado: Parte 1, CI/CD e Deploy

*Instituto NTA (Instituto Nacional de Tecnologia Aplicada). Apostila do aluno, Parte 1 de 3, 24/09. Professor: Thiago Azeredo Rodrigues.*

Do chat personalizado à URL pública, com Git, GitHub Actions e Hugging Face Spaces. Parte 2 (01/10): RAG e Base de Conhecimento. Parte 3 (08/10): Front-end com IA e Deploy em Produção.

*Convertido do PDF para Markdown em 01/10/2026. O diagrama do original está descrito em texto, em bloco de citação.*

## 01 Como vamos trabalhar: desenvolvimento orientado a especificação
Hoje você vai construir e publicar um chat de IA com a sua cara. Mas o jeito de construir importa tanto quanto o resultado, e é por ele que começamos.

### O problema de pedir "faz um chat para mim"
Um assistente de programação como o Claude Code ou o Codex escreve código muito rápido. Se você pede algo vago, ele não para para perguntar: ele decide sozinho dezenas de coisas (qual biblioteca, onde fica a chave, como validar a configuração, o que acontece quando dá erro) e entrega um resultado que parece pronto. Você só descobre as decisões ruins depois, quando algo quebra. Esse jeito de trabalhar, pedindo e aceitando o que vier, costuma ser chamado de _vibe coding_.

### O que é spec-driven
**Desenvolvimento orientado a especificação** (_spec-driven development_) inverte a ordem: antes de qualquer código, existe um documento que diz o que será construído, como, e como saber que ficou certo. Esse documento é a **spec**. O código vem depois, em tarefas pequenas, e cada tarefa é conferida contra a spec.

|**Etapa**|**Arquivo**|**Quem escreve**|**O que contém**|
|---|---|---|---|
|1. Ideia|`IDEIA-parte1.md`|Você, em linguagem simples|O que você quer, para quem, o que não entra agora e como saber que deu certo|
|2. Spec|`SPEC-parte1-cicd-deploy.md`|O assistente, depois de te fazer perguntas. Você revisa e aprova|Decisões técnicas, contrato da configuração, requisitos (RF1, RF2...), testes (T1, T2...), critérios de aceite e ordem das tarefas|
|3. Tarefas|O código do projeto|O assistente, uma tarefa por vez|Só o que a tarefa da vez pede, com instrução de como testar|
|4. Verificação|`testes.py` no CI|Nasce dos itens T da spec|Confere, a cada commit, se o projeto ainda cumpre a spec|

### Por que funciona melhor com IA
- **As decisões aparecem antes do código.** Você lê "a chave fica no Space, nunca no repositório" na spec e aprova ou corrige, sem precisar ler Python.

- **Tarefas pequenas erram menos.** Pedir "implemente a tarefa 3" dá ao assistente um alvo claro e fácil de conferir.

- **A spec fica no repositório.** Ela é versionada como o código, e amanhã, com outro assistente ou outra pessoa, o projeto continua de onde parou.

- **Os critérios de aceite dizem quando acabou.** Sem eles, sempre dá para pedir "só mais um ajuste".

##### Spec e CI/CD são as duas metades da mesma ideia
A spec diz o que é certo. O portão de testes no GitHub Actions confere isso sozinho, a cada commit. Spec sem portão é promessa; portão sem spec é teste sem critério. É por isso que os testes do projeto são numerados T1, T2, T3: cada um corresponde a um item da spec.

##### Você decide, o assistente executa
A etapa mais importante do processo é a que tem menos código: ler a spec e aprovar. Tudo que você deixar passar ali, o assistente vai construir com muita competência, inclusive o que estiver errado.

### Onde rodar o assistente
O Claude Code e o Codex rodam no terminal, em aplicativos de desktop e em versões web que se conectam ao seu repositório do GitHub. Ambos exigem plano pago; confira as condições atuais de cada um. Quem não tiver acesso acompanha a demonstração na tela e usa o **projeto de referência** do professor, que foi construído a partir da mesma ideia e segue a mesma spec. O deploy, que é o assunto central da aula, é idêntico nos dois casos.

## 02 O que você vai construir hoje
Um assistente de IA com a sua cara: nome, cores, logo e especialidade escolhidos por você, publicado numa URL que qualquer pessoa abre no navegador. E, junto com ele, um **processo automático de publicação**: toda vez que você alterar algo no repositório, o assistente é testado e republicado sozinho.

> **Diagrama: o caminho de uma alteração, em cinco etapas.**
>
> 1. **Você** edita o `config.yml` no site do GitHub e faz commit (push).
> 2. **GitHub Actions**, numa máquina Linux descartável: o job *testar* roda o `testes.py`; se passou, o job *publicar* envia os arquivos ao Space (usa o secret `HF_TOKEN`).
> 3. **Hugging Face Space:** recebe os arquivos, instala e roda o `app.py` (usa o secret com a chave do modelo) e chama o modelo.
> 4. **OpenRouter:** repassa a conversa ao modelo escolhido e devolve a resposta aos poucos.
> 5. **Qualquer pessoa** abre a URL do Space e conversa com o seu assistente.
>
> **Portão:** se o `testes.py` falhar, o job *publicar* nem começa e nada é publicado.

### O que você precisa ter
|**Conta ou item**|**Para quê**|**Onde**|
|---|---|---|
|Conta no GitHub|Guardar o código e rodar a automação (Actions)|github.com|
|Conta no Hugging Face|Hospedar o assistente (Spaces)|huggingface.co|
|Conta e chave no OpenRouter|O assistente conversar com o modelo. Há modelos gratuitos|openrouter.ai|
|Claude Code ou Codex (opcional)|Gerar a spec e o código a partir da sua ideia|Plano pago de cada serviço|
|Um navegador|Todo o resto|Nada a instalar para o deploy|

## 03 O que é deploy
Enquanto um programa roda só no seu computador, ele existe só para você: para quando você desliga a máquina, não tem endereço público e depende de tudo que está instalado ali.

**Deploy** (implantar, publicar, colocar no ar) é levar a aplicação para um ambiente onde outras pessoas conseguem usar: com endereço, ligada o tempo todo e independente do seu computador. Um deploy bem feito responde a três perguntas:

- **Onde a aplicação roda?** Numa máquina de um provedor (GitHub, Hugging Face, Render, Azure).

- **Como ela chega lá?** Manualmente (alguém sobe arquivos) ou automaticamente (um processo faz isso a cada mudança).

- **Onde ficam os segredos?** Chaves e senhas nunca vão junto com o código; ficam guardadas no ambiente que executa.

##### A frase que resume o problema
"Na minha máquina funciona." Deploy é o conjunto de práticas que faz a aplicação funcionar também na máquina dos outros, do mesmo jeito, toda vez.

## 04 Tipos de deploy
Existem dezenas de serviços, mas eles se organizam em poucas categorias. O que muda é quanto controle você tem e quanto trabalho de infraestrutura fica com você.

|**Tipo**|**O que o servidor faz**|**Exemplos**|**Bom para**|
|---|---|---|---|
|Site estático|Entrega arquivos prontos (HTML, CSS, JS). Não executa nada.|GitHub Pages, Netlify, Cloudflare Pages|Portfólio, documentação, painéis gerados antes|
|Plataforma de apps (PaaS)|Executa o seu código: você entrega o projeto, ela cuida da máquina.|Hugging Face Spaces, Render, Railway|Protótipos, demos de IA, APIs pequenas|
|Nuvem gerenciada|Executa o seu código com rede, identidade, escala e monitoramento corporativos.|Azure App Service, AWS, Google Cloud Run|Produção em empresa|
|Serverless|Executa uma função só quando é chamada; cobra por execução.|Azure Functions, AWS Lambda|Tarefas curtas e eventuais|
|Plataforma de agentes|Executa e monitora agentes de IA prontos, com rastreamento embutido.|CrewAI AMP e similares|Sistemas multiagente em empresa|

### A pergunta que decide
**A aplicação precisa executar código quando alguém acessa?** Se não, site estático resolve e é gratuito. Se sim, você precisa de um serviço que execute código. E há uma segunda pergunta, que costuma decidir sozinha: **a aplicação usa algum segredo?**

##### Por que o nosso chat não pode ir para o GitHub Pages
Cada pergunta do usuário exige uma chamada ao modelo, e essa chamada exige a chave da API. Num site estático, todo o código vai para o navegador do visitante. Se a chave estiver ali, qualquer pessoa abre o código-fonte da página e copia.

E não adianta guardar a chave nos secrets do GitHub: eles existem só durante a execução do Actions. O Pages nunca tem acesso a eles, e escrever a chave no JavaScript durante o build é publicá-la. Secret no GitHub serve para o que o Actions faz, não para o que o visitante faz.

### Por que Hugging Face Spaces hoje
- **Executa Python e guarda segredos**, o que o chat exige.

- **Gratuito no hardware padrão (ZeroGPU)**, mais que suficiente para um chat que só repassa perguntas ao modelo.

- **Não puxa código do GitHub sozinho**: quem publica é o GitHub Actions. Isso torna a automação visível, que é o que queremos aprender.

- **Gradio é nativo**: a biblioteca de interface que usamos roda sem configuração extra.

**E o Render?** Também serviria, e é mais parecido com um serviço de nuvem corporativo. Mas ele se conecta direto ao GitHub e publica sozinho (o Actions ficaria de enfeite), e no plano gratuito dorme após cerca de 15 minutos sem acesso, levando perto de um minuto para acordar. Ele volta a ser útil na Parte 3, para backends que não são Gradio. Limites de planos gratuitos mudam: confira na documentação antes de usar em algo sério.

### OpenRouter: um endereço, vários modelos
O Space executa o chat, mas quem gera as respostas é um modelo de linguagem de outro fornecedor. Usamos o **OpenRouter**, um intermediário que dá acesso a modelos de vários fornecedores (Claude, GPT, Gemini, Llama e outros) com uma única conta e uma única chave. Ele usa o formato da API da OpenAI, que virou padrão de mercado: trocar de fornecedor é trocar endereço, chave e nome do modelo, não o código.

|**Aspecto**|**Como funciona**|
|---|---|
|Modelos gratuitos|Os que terminam em `:free` não cobram por token. `openrouter/free` escolhe automaticamente um gratuito disponível|
|Limites do gratuito|20 requisições por minuto e 50 por dia; 1.000 por dia depois de comprar ao menos 10 dólares em créditos, em qualquer momento|
|Modelos pagos|Ex.:`anthropic/claude-haiku-4.5`. Cobrados por uso, a partir dos créditos da conta|
|Cuidados|Modelos gratuitos podem sair do ar sem aviso, respondem pior em português e muitos exigem liberar o registro dos dados nas configurações de privacidade|

##### Nunca coloque dado sensível num modelo gratuito
Se o provedor registra as conversas, o que for digitado no chat pode ser guardado por terceiros. Para demonstração, tudo bem; para dado de cliente, use um modelo pago com política de dados clara. Os limites dos planos gratuitos mudam: confira em openrouter.ai.

## 05 Git e GitHub: o mínimo
**Git** é um programa que guarda o histórico de uma pasta. **GitHub** é um site que hospeda essas pastas e acrescenta coisas em volta, entre elas a capacidade de executar automações. Analogia: o Git é o controle de versões do documento; o GitHub é o Google Drive que guarda, compartilha e ainda faz coisas com o arquivo.

|**Termo**|**O que é**|
|---|---|
|Repositório|Uma pasta com histórico. "Repo", para os íntimos.|
|Commit|Uma fotografia do estado da pasta, com uma mensagem explicando o que mudou. Quando você edita um arquivo no site e clica em **Commit changes**, está criando um.|
|Push|Enviar commits para o repositório no GitHub. É o verbo que dispara a automação. Pelo site não existe botão de push: o commit já nasce no GitHub, e para o Actions isso conta como push.|
|Branch|Uma linha paralela de trabalho. Hoje usamos só a principal, a **main**.|

##### Público ou privado
Repositório público: qualquer pessoa vê o código. Privado: só quem você autorizar. Para aprender, público funciona bem, desde que nunca exista senha, chave ou dado pessoal dentro dele. O portão de testes verifica isso por você.

## 06 Por que existe linha de comando
O terminal é uma forma de conversar com o computador escrevendo em vez de clicando. É **repetível** (o mesmo comando roda igual mil vezes), **automatizável** (um robô não clica em botão, mas executa comando) e é **o que existe no servidor** (a máquina na nuvem não tem tela).

Por isso o arquivo de automação é uma lista de comandos. Quando você lê `python testes.py` dentro do YAML, está lendo o que você digitaria no terminal, só que quem digita é o GitHub. Automatizar é escrever o que você faria à mão.

## 07 CI/CD
**CI, Integração Contínua.** Toda vez que o código muda, verificações automáticas rodam: os arquivos estão válidos? os testes passam? Serve para descobrir que algo quebrou em minutos, não em semanas.

**CD, Entrega ou Implantação Contínua.** Se as verificações passaram, o resultado segue para o ar sem ninguém subir arquivo à mão. A diferença entre as duas versões do CD é quem aperta o botão final:

|**Modalidade**|**Quem publica**|
|---|---|
|Entrega contínua (delivery)|Fica tudo pronto e testado; uma pessoa aprova a publicação.|
|Implantação contínua (deployment)|Publica sozinho, sem aprovação humana.|

### No projeto de hoje
| Parte | No nosso projeto |
|---|---|
| **CI** | O job **testar** roda o `testes.py`, com as verificações T1 a T9 da spec: configuração válida, campos preenchidos, cores legíveis, logo aceita, modelo no formato certo, Python sem erro e nenhuma chave esquecida nos arquivos. |
| **CD** | O job **publicar** envia o repositório para o Space, que reconstrói e reinicia o assistente. É implantação contínua: passou no teste, vai para o ar. |

##### Com IA no meio, a pergunta muda
Publicar sozinho um arquivo de configuração é tranquilo. Publicar sozinho algo que um modelo gerou, e que pessoas vão ler, é uma decisão séria. O teste deixa de conferir "a resposta certa" (saída de modelo varia) e passa a conferir se a saída está dentro de critérios. Voltaremos a isso na Parte 2.

## 08 GitHub Actions: a máquina descartável
Quando o processo dispara, o GitHub liga um computador novo, uma máquina virtual Linux limpa que não existia segundos antes. Ela:

1. baixa uma cópia do seu repositório;

2. executa, em ordem, os comandos que você escreveu no YAML;

3. entrega o resultado (no nosso caso, envia os arquivos ao Hugging Face);

4. é destruída.

Nada sobrevive entre uma execução e outra. Se o processo instalou o Python, a próxima execução instala de novo.

##### O erro de raciocínio mais comum
Achar que o Actions roda no seu computador, ou que o GitHub "entende" seu Python. Ele liga um Linux vazio e digita seus comandos. Se o comando funciona num terminal, funciona ali; se não funciona, ali também não vai funcionar.

|**Termo**|**O que é**|
|---|---|
|Workflow|O processo inteiro, descrito num arquivo `.yml` dentro de `.github/workflows/`|
|Trigger (gatilho)|O que faz o processo começar|
|Job|Um bloco de trabalho, que roda numa máquina. Nosso workflow tem dois: testar e publicar|
|Step (passo)|Um comando ou uma ação dentro do job|
|Runner|A máquina descartável que executa tudo|
|Action|Um pedaço de automação pronto, feito por outra pessoa (ex.: `actions/checkout`)|

| Gatilho | Quando dispara | Usamos hoje? |
|---|---|---|
| `push` | Alguém enviou código novo (inclui editar e dar commit pelo site) | Sim |
| `workflow_dispatch` | Botão **Run workflow**, apertado por uma pessoa na aba Actions | Sim |
| `schedule` | Horário marcado, no formato cron. Ex.: `'0 11 * * *'` é todo dia às 11h UTC, ou seja, 8h de Brasília | Não; útil quando os dados mudam sozinhos |

## 09 Segredos: onde fica cada chave
Chave de API nunca vai dentro do repositório. Neste projeto existem **duas** chaves, e cada uma fica num lugar diferente.

##### O segredo fica com quem executa
Quem precisa usar a chave é a máquina que roda o comando. Então é ali que ela é cadastrada.

|**Nome exato**|**Quem usa**|**Onde cadastrar**|
|---|---|---|
|`OPENROUTER_API_KEY`|O app.py, rodando no Space, a cada pergunta do usuário. Valor começa com `sk-or-`|Hugging Face: Space, **Settings**, **Variables and secrets**, **New secret**|
| `HF_TOKEN` | O runner do GitHub Actions, para enviar os arquivos ao Space. Valor começa com `hf_` | GitHub: repositório, **Settings**, **Secrets and variables**, **Actions**, **New repository secret** |

Os nomes precisam ser exatamente esses, em maiúsculas e com sublinhado: o código procura por eles. A chave do OpenRouter **não** vai no GitHub, porque nenhum passo do Actions chama o modelo. No Space ela é lida assim:

```
CHAVE = os.environ.get("OPENROUTER_API_KEY")
```

##### Chave commitada por engano é chave vazada
Mesmo depois de apagada, ela continua no histórico do Git, e robôs varrem repositórios públicos atrás disso. Se acontecer, **revogue a chave** no painel do provedor e gere outra. Tentar esconder não resolve.

**Token Write ou Fine-grained?** O token Write do Hugging Face é o mais simples, mas dá escrita em **todos** os seus repositórios de lá. Em projeto real, prefira um Fine-grained restrito ao Space, ou o recurso **Trusted Publishers** do Space, que deixa o Actions publicar sem nenhum token guardado.

## 10 YAML em cinco regras
YAML é um formato de arquivo de configuração: uma lista de coisas com nome. Aqui há dois: o `config.yml` (seu assistente) e o `deploy.yml` (o processo).

##### 1. chave: valor
```
nome: Professor de Dados e IA
```

**2. A indentação define o que está dentro de quê.** Só espaços, nunca Tab.

```
jobs:
  testar:
    runs-on: ubuntu-latest
```

##### 3. O hífen cria item de lista.
```
exemplos:
  - O que é RAG?
  - Como funciona um ETL?
```

##### 4. A barra vertical | guarda várias linhas.
```
prompt_sistema: |
  Você é um professor de engenharia de dados.
  Responda em português do Brasil.
```

**5. # é comentário.** E cor hexadecimal vai entre aspas, porque # sozinho começa um comentário: `cor_principal: "#0B2A5B"`.

## 11 Da ideia à spec, passo a passo
### Etapa 1: escreva a sua ideia
Crie no repositório o arquivo `IDEIA-parte1.md` (**Add file**, **Create new file**). Não é preciso saber programar: é um texto em linguagem simples. O modelo completo está no Apêndice A; adapte ao seu assunto. Uma boa ideia tem estas seções:

|**Seção**|**Pergunta que responde**|
|---|---|
|O que eu quero|O que o assistente faz e sobre qual assunto|
|Qual IA eu quero usar|Quem fornece o modelo (OpenRouter) e por quê|
|Como eu quero personalizar|O que precisa ser trocável sem mexer em código|
|Como eu quero publicar|Onde fica o código, onde roda, quando atualiza, o que confere antes|
|Segurança|Onde ficam as chaves e o que acontece se alguém errar|
|O que NÃO entra agora|Os limites do escopo. Esta seção evita metade dos problemas|
|Como vou saber que deu certo|Os testes que você mesmo faria para aceitar o resultado|

### Etapa 2: peça a spec
Abra o Claude Code ou o Codex na pasta do repositório e cole o prompt abaixo. Repare em três escolhas dele: o assistente **pergunta antes** de decidir, a saída tem **formato fixo** em dez seções, e ele **para e espera** a sua aprovação.

```
Leia o arquivo IDEIA-parte1.md. Ele descreve, em linguagem simples, o projeto
que eu quero construir.

Antes de escrever qualquer coisa, me faça as perguntas que faltarem para você
decidir (por exemplo: qual modelo do OpenRouter usar, meu usuário no Hugging
Face, o nome do Space, se o Space usa CPU ou ZeroGPU). Faça no máximo 5
perguntas, uma lista só.

Depois, gere o arquivo SPEC-parte1-cicd-deploy.md no formato spec-driven, com:
1. Objetivo, público e escopo (o que entra e o que fica para as partes 2 e 3)
2. Stack escolhida (a IA é acessada pelo OpenRouter) e restrições conhecidas
   do Hugging Face Spaces
3. Estrutura de arquivos do projeto
4. Contrato do arquivo de configuração: cada campo, se é obrigatório, valores
   aceitos e padrão
5. Requisitos funcionais numerados (RF1, RF2...)
6. Verificações do portão de testes numeradas (T1, T2...)
7. Pipeline de deploy com GitHub Actions e o que eu preciso configurar à mão
8. Critérios de aceite em formato de checklist
9. Ordem das tarefas de implementação, uma de cada vez
10. Erros comuns e como resolver

Escreva em português, para um iniciante entender.
Não escreva código ainda: só a spec. Quando terminar, me mostre o resumo e
espere a minha aprovação.
```

### Etapa 3: revise antes de aprovar
Leia a spec procurando decisões, não erros de digitação. Antes de aprovar, confira:

- A chave aparece como secret no Space, e em nenhum arquivo do repositório?

- Cada campo da configuração tem valores aceitos e padrão definidos? (Ex.: o que acontece com uma cor inválida?)

- Cada item de "Como vou saber que deu certo" da sua ideia virou critério de aceite?

- Os testes T cobrem os erros que você mesmo cometeria: campo vazio, cor errada, logo ausente, chave no código?

- O que ficou para as Partes 2 e 3 está explicitamente fora do escopo?

- As restrições do Hugging Face estão lá: hardware ZeroGPU, logo sem .png e .jpg, histórico completo no envio?

Se algo estiver errado, peça a correção em linguagem normal ("o portão também deve barrar cores claras demais para texto branco") e revise de novo. Só então aprove.

### Etapa 4: uma tarefa por vez
Com a spec aprovada, peça: **"Implemente a tarefa 1 da spec e me mostre como testar."** Teste, faça commit e só então peça a tarefa 2. Cada commit dispara o portão, então você descobre na hora se uma tarefa quebrou o que a anterior fez.

##### Se o tempo apertar
Gerar a spec e implementar todas as tarefas leva tempo, e cada pessoa terá um código um pouco diferente. Se o seu não ficar pronto durante a aula, use o projeto de referência para fazer o deploy e termine o seu em casa: o processo de publicação é o mesmo.

## 12 O projeto de referência por dentro
O professor construiu este projeto a partir da mesma ideia, seguindo o processo acima. Use-o para comparar com o seu: os nomes podem variar, mas as decisões devem ser equivalentes.

```
assistente-ia/
├── .github/workflows/
│   └── deploy.yml        o processo: testar e publicar
├── IDEIA-parte1.md       a ideia, em linguagem simples
├── SPEC-parte1-...md     a spec aprovada (gerada pelo assistente)
├── app.py                o chat
├── config.yml            SEU assistente: textos, cores, logo, modelo, prompt
├── logo.svg              a logo
├── testes.py             o portão, com as verificações T1 a T9
├── requirements.txt      bibliotecas que o Space instala
└── README.md             cabeçalho lido pelo Hugging Face
```

### Contrato do config.yml
|**Campo**|**Obrigatório**|**Valores aceitos**|
|---|---|---|
|`nome`,`descricao`|Sim|Texto livre. Título e subtítulo no topo|
|`cor_principal`|Sim|Hexadecimal `"#RRGGBB"`, entre aspas, escura o bastante para texto branco (contraste mínimo 3:1)|
|`cor_secundaria`|Não|Mesmo formato. Se preenchida, o fundo vira um degradê|
|`logo`|Não|Arquivo .svg no repositório ou link https|
|`logo_tamanho`|Não|Número entre 32 e 160 (pixels). Padrão: 72|
|`modelo`|Sim|Formato empresa/modelo do OpenRouter. Ex.: `openrouter/free`|
|`max_tokens`|Não|Tamanho máximo da resposta. Padrão: 800|
|`prompt_sistema`|Sim|Papel, público, formato e limites do assistente. Mínimo de 80 caracteres|
|`exemplos`|Não|Lista de perguntas que aparecem como botões|

O prompt de sistema é onde está a inteligência do seu assistente. Um bom prompt define **papel**, **público**, **formato** (tamanho, idioma, tom) e **limites** (o que não inventar, o que recusar).

### app.py em quatro ideias
1. **Lê o config.yml** e monta a página com o Gradio: topo com logo, nome e descrição sobre o fundo nas suas cores, e o chat num cartão branco, fácil de ler.

2. **Pega a chave do ambiente**, nunca do código, e conversa com o OpenRouter no formato da OpenAI. Sem chave, o chat avisa qual secret cadastrar.

3. **Reenvia a conversa inteira a cada pergunta.** O modelo não tem memória própria: quem lembra é o app.

4. **Responde aos poucos (streaming)**, como os chats comerciais.

```
cliente = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=CHAVE)
fluxo = cliente.chat.completions.create(
    model=CONFIG["modelo"],        # trocar de modelo = trocar esta linha no config
    messages=mensagens,             # prompt de sistema + conversa inteira
    stream=True,
)
for evento in fluxo:                # a tela atualiza a cada pedaço
    ...
```

O Gradio é uma biblioteca Python da mesma família do Streamlit: gera a página sem você escrever HTML. O Streamlit nasceu para painéis de dados; o Gradio, para demonstrar modelos de IA, e tem o componente `gr.ChatInterface`, que monta um chat completo em poucas linhas. Ele também entrega uma API pronta, que usaremos na Parte 3.

**Um detalhe do hardware:** o ZeroGPU exige ao menos uma função marcada com `@spaces.GPU`. Nosso app não usa GPU, então há uma função `_reserva_gpu` que existe só para satisfazer essa regra e nunca é chamada.

### testes.py: o portão
|**Item**|**Verifica**|**Por quê**|
|---|---|---|
|T1|config.yml é YAML válido|Um espaço fora do lugar quebraria o app|
|T2|Campos obrigatórios preenchidos|Sem nome ou prompt, a página sai incompleta|
|T3|Cores no formato #RRGGBB|"azul" não é uma cor que o CSS entenda|
|T4|Contraste com texto branco de no mínimo 3:1|Uma cor clara deixaria o topo e os botões ilegíveis|
|T5|Logo existe, é .svg ou link, e tem tamanho entre 32 e 160|O Hugging Face recusa .png e .jpg enviados sem configuração extra|
|T6|Modelo no formato empresa/modelo|O OpenRouter recusaria o nome|
|T7|Prompt com pelo menos 80 caracteres|Prompt de uma linha gera assistente genérico|
|T8|app.py sem erro de sintaxe|Erro descoberto em segundos, não depois do build|
|T9|Nenhuma chave de API nos arquivos|Barra o vazamento antes de ele chegar ao público|

Repare no T4: ele não confere se o arquivo está "certo", e sim se o resultado é **legível**. Portão bom testa qualidade, não só sintaxe.

### deploy.yml: o processo, bloco a bloco
```
# versão resumida: no arquivo real, cada passo tem um nome
env:
  HF_USUARIO: seu-usuario       # EDITE: seu usuário no Hugging Face
  HF_SPACE: meu-assistente      # EDITE: nome exato do Space
on:
  push:
    branches: [main]            # todo commit na main dispara
  workflow_dispatch:            # botão Run workflow
jobs:
  testar:                       # job 1: o portão
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install pyyaml
      - run: python testes.py
  publicar:                     # job 2: só roda se o testar passou
    needs: testar
    runs-on: ubuntu-latest      # outra máquina, nova e limpa
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # histórico completo, exigido pelo HF
      - env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          REPO="huggingface.co/spaces/${HF_USUARIO}/${HF_SPACE}"
          git push --force "https://${HF_USUARIO}:${HF_TOKEN}@${REPO}" HEAD:main
```

A linha `needs: testar` é o que transforma o teste em portão. E o README.md também tem função técnica: o cabeçalho entre as linhas `---` diz ao Hugging Face que o Space é Gradio, qual versão usar e qual arquivo executar.

## 13 Passo a passo do deploy
### A. Seu repositório no GitHub
1. Se você gerou o projeto com o assistente, ele já está no seu repositório. Se vai usar o projeto de referência: abra o repositório do professor, clique em **Use this template**, **Create a new repository**, deixe **Public** e crie.

2. Se recebeu os arquivos em .zip: crie um repositório vazio, **Add file**, **Upload files**, e arraste o **conteúdo** da pasta, não a pasta. Confira se `.github/workflows` subiu.

### B. O Space no Hugging Face
1. Em huggingface.co, **New**, **Space**. Nome (ex.: `meu-assistente`), SDK **Gradio**, template **Blank**, hardware **ZeroGPU** (o gratuito disponível; sem assinatura PRO não é possível trocar para CPU basic depois), visibilidade **Public**. Ignore o código de exemplo que o Space mostra: os arquivos chegam pelo GitHub.

2. Confira na URL o nome exato do Space. Ele será o `HF_SPACE`.

3. No Space: **Settings**, **Variables and secrets**, **New secret**. Nome `OPENROUTER_API_KEY`, valor: sua chave do OpenRouter.

### C. A ponte entre os dois
1. No Hugging Face: foto do perfil, **Settings**, **Access Tokens**, **Create new token**, tipo **Write**. Copie o valor na hora; ele só aparece uma vez.

2. No GitHub: **Settings**, **Secrets and variables**, **Actions**, **New repository secret**. Nome `HF_TOKEN`.

3. Por último, edite `.github/workflows/deploy.yml` pelo lápis: `HF_USUARIO` e `HF_SPACE` com os seus dados, exatamente como aparecem na URL do Space. **Commit changes**.

### D. O primeiro deploy
1. O commit anterior já disparou o processo. Aba **Actions**, clique na execução em andamento.

2. Verde nos dois jobs: os arquivos chegaram ao Space.

3. No Space, espere **Building** virar **Running**. Converse com o assistente.

### E. Personalize
1. Edite o `config.yml` pelo lápis: nome, descrição, cores, prompt e exemplos do **seu** assunto. Commit.

2. Acompanhe o novo deploy e confira o resultado no Space.

### F. Veja o portão funcionando
1. Troque `cor_principal` para `"#FFD966"` (um amarelo claro) e faça commit.

2. Na aba Actions: o job **testar** fica vermelho e o **publicar** nem começa. A mensagem explica que o texto branco ficaria ilegível.

3. Abra o Space: a versão anterior continua no ar, intacta. É isso que o portão protege.

4. Volte para uma cor escura, faça commit e veja o verde voltar.

## 14 Por que o chat esquece
Converse, feche a aba e abra de novo: a conversa sumiu. Não é defeito; são dois tipos diferentes de memória.

|**Tipo**|**Como funciona**|**Precisa de banco?**|
|---|---|---|
|Memória da conversa|Enquanto a aba está aberta, o app guarda o histórico da sessão e reenvia tudo ao modelo a cada pergunta.|Não. É o que temos hoje.|
|Histórico salvo|A conversa sobrevive ao fechamento da aba, ou você lê depois o que os visitantes perguntaram.|Sim.|

E não adianta gravar num arquivo dentro do Space: o disco dele é apagado a cada reinício ou novo deploy, pelo mesmo motivo que o runner do Actions é descartável. **Tudo que precisa sobreviver vai para fora da máquina**, num banco de dados como o Supabase.

##### Guardar conversa é tratar dado pessoal
Se um dia você salvar o que os visitantes digitam, isso entra na LGPD: é preciso avisar na página o que é guardado, para quê e por quanto tempo. Decida isso antes de ligar o banco.

##### Próximos encontros
**Parte 2 (01/10): RAG e Base de Conhecimento.** O assistente passa a responder com base em documentos da sua área. A cada push, o Actions reconstrói o índice de busca e roda perguntas de teste antes de publicar. Traga de 3 a 5 documentos em texto ou Markdown.

**Parte 3 (08/10): Front-end com IA e Deploy em Produção.** Uma interface profissional, gerada com IA, publicada no GitHub Pages e conectada a este mesmo backend. Traga a logo em SVG e as cores que quer usar.

## 15 Erros comuns na primeira vez
|**Sintoma**|**Causa provável**|**Conserto**|
|---|---|---|
|Job testar vermelho|O portão encontrou um problema|Abra o passo "Rodar o portão" e leia a lista impressa|
|O workflow não aparece na aba Actions|O arquivo não está em `.github/workflows/`, ou a pasta com ponto não subiu no upload|Add file, Create new file, digite `.github/workflows/deploy.yml` e cole o conteúdo|
|Publicar falha com Authentication failed ou 403|`HF_TOKEN` ausente, com outro nome ou do tipo Read|Gere um token Write e cadastre com o nome exato|
|Repository not found|`HF_USUARIO` ou `HF_SPACE` diferente do Space|Copie exatamente da URL do Space, letra por letra|
|Push rejeitado por arquivo binário|Imagem .png ou .jpg no repositório|Use logo .svg ou link https e apague a imagem|
|did not find expected key|Tab ou indentação desalinhada no YAML|Só espaços; confira a linha citada|
|Cor aceita como comentário e campo vazio|Cor sem aspas: `cor_principal: #0B2A5B`|Coloque entre aspas:`"#0B2A5B"`|
|Space em Build error|Cabeçalho do README.md apagado ou alterado|Aba Logs do Space; restaure o cabeçalho|
|Space em Runtime error citando spaces.GPU|ZeroGPU exige ao menos uma função com @spaces.GPU|Confira se o app.py tem a função _reserva_gpu|
|Chat avisa que a chave não foi configurada|Secret ausente no Space ou com outro nome|Cadastre `OPENROUTER_API_KEY` e reinicie (Settings, Restart)|
|Erro 401 na resposta|Chave do OpenRouter inválida ou revogada|Gere outra em openrouter.ai e atualize o secret|
|Erro 402 na resposta|Modelo pago sem crédito na conta|Use um modelo `:free` ou adicione crédito|
|Erro 429 na resposta|Limite do gratuito atingido|Espere um minuto; se for o limite diário, só no dia seguinte|
|Modelo gratuito recusado|Privacidade bloqueia provedores que registram dados, ou o modelo saiu do ar|Ajuste a privacidade no OpenRouter ou troque o modelo|
|Actions verde, Space com versão antiga|O Space ainda está reconstruindo|Espere Running e recarregue|
|Space mostra Sleeping|Muito tempo sem acesso|Abra a página; ele acorda em instantes|

## 16 Apêndice A: modelo de ideia
Este é o `IDEIA-parte1.md` usado no projeto de referência. Copie e troque o assunto, as cores e o que mais for seu.

```markdown
# Ideia do projeto · Parte 1: meu primeiro assistente de IA no ar

> Este texto conta, em linguagem simples, o que eu quero construir.
> Não é preciso saber programar para escrevê-lo. No final há um prompt para pedir ao Claude
> Code (ou ao Codex) que transforme esta ideia numa spec técnica.

## O que eu quero
Quero colocar na internet um chat com inteligência artificial que responda dúvidas sobre um
assunto que eu escolher. Qualquer pessoa deve conseguir abrir um link e conversar com ele.

No meu caso, o assistente vai ajudar alunos com dúvidas sobre engenharia de dados e
Inteligência Artificial, explicando de forma didática, como um professor.

## Qual IA eu quero usar
Quero usar o OpenRouter. Com uma única conta e uma única chave, ele dá acesso a modelos de
vários fornecedores (Claude, GPT, Gemini, Llama e outros). Assim eu posso trocar de modelo
só mudando o nome dele na configuração, sem mexer no código e sem criar conta em cada
empresa.

## Como eu quero personalizar
Não quero mexer em código para mudar o assistente. Quero um único arquivo de configuração
onde eu consiga trocar:
- o nome do assistente e uma frase de descrição;
- as cores da página (uma ou duas cores);
- a logo e o tamanho dela;
- qual modelo do OpenRouter ele usa (por exemplo, `anthropic/claude-haiku-4.5`) e o tamanho
  máximo das respostas;
- as instruções de comportamento: quem ele é, com quem fala, o que ele não deve fazer;
- algumas perguntas de exemplo que aparecem como botões para o usuário clicar.

Quero editar esse arquivo pelo próprio site do GitHub, sem instalar nada.

## Como eu quero publicar
- O código fica no GitHub.
- O chat fica publicado de graça no Hugging Face Spaces.
- Toda vez que eu salvar uma alteração no GitHub, o site deve atualizar sozinho.
- Antes de publicar, alguma coisa precisa conferir se eu não errei na configuração (uma cor
  que não existe, um campo vazio, uma logo que não está lá). Se eu errar, a publicação para
  e o site antigo continua no ar, com uma mensagem dizendo o que corrigir.

## Segurança
- A chave do OpenRouter não pode aparecer no código nem no GitHub. Ela deve ficar guardada
  nas configurações do Hugging Face.
- Se alguém colocar uma chave no código por engano, a publicação deve ser bloqueada.

## Aparência
- A página deve ter a logo, o nome e a descrição no topo.
- O fundo deve usar as cores que escolhi, e o chat deve ficar fácil de ler.
- Tudo o que aparece na tela deve estar em português.

## O que NÃO entra agora
- Base de conhecimento com os meus próprios documentos (fica para a parte 2).
- Um site próprio, com domínio próprio e visual feito do zero (fica para a parte 3).
- Login de usuários e conversas salvas.

## Como vou saber que deu certo
- Eu abro o link e converso com o assistente.
- Eu mudo uma cor ou uma pergunta de exemplo pelo GitHub, e minutos depois o site mostra a mudança.
- Eu erro de propósito na configuração, a publicação é barrada e o site antigo continua funcionando.
```

## 17 Apêndice B: rodar na sua máquina
Opcional. Serve para testar mudanças antes de subir, e é o ambiente natural do Claude Code e do Codex no terminal.

- **Windows:** Git for Windows (git-scm.com), que traz o Git Bash, e Python (python.org), marcando **Add Python to PATH**.

- **macOS:** no Terminal, `git --version` oferece instalar as ferramentas. Python em python.org ou `brew install python git`.

- **Linux:** `sudo apt install git python3 python3-pip` (Debian e Ubuntu).

```
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>
pip install gradio==5.49.1 openai pyyaml
python testes.py                       # o mesmo portão do Actions
export OPENROUTER_API_KEY=sua-chave    # PowerShell: $env:OPENROUTER_API_KEY="sua-chave"
python app.py                          # abra http://localhost:7860
```

## 18 Glossário
**Action**: automação pronta de terceiros, reaproveitada no workflow.

**Branch**: linha paralela de desenvolvimento.

**Build**: etapa em que o serviço instala dependências e prepara a aplicação para rodar.

**CD**: entrega ou implantação contínua.

**CI**: integração contínua.

**Commit**: fotografia do estado do repositório, com mensagem.

**Critério de aceite**: condição verificável que diz quando uma entrega está pronta.

**Cron**: formato para marcar horário de execução recorrente, em UTC no GitHub.

**Deploy**: colocar a aplicação no ar para outras pessoas usarem.

**Gradio**: biblioteca Python que gera interfaces web para modelos de IA.

**Job**: bloco de trabalho dentro de um workflow, executado numa máquina.

**OpenRouter**: serviço que dá acesso a modelos de vários fornecedores por uma única API, com opções gratuitas.

**PaaS**: plataforma que executa seu código cuidando da infraestrutura.

**Portão**: etapa de teste que precisa passar para a publicação acontecer.

**Prompt de sistema**: instrução fixa que define papel, público, formato e limites do assistente.

**Push**: enviar commits para o repositório remoto.

**Requisito funcional**: o que o sistema deve fazer, numerado na spec como RF1, RF2.

**Runner**: máquina descartável que executa o workflow.

**Secret**: valor sensível guardado cifrado e injetado na execução.

**Spec**: documento que define o que será construído, como e como verificar.

**Spec-driven**: desenvolvimento em que a spec vem antes do código e guia cada tarefa.

**Space**: aplicação hospedada no Hugging Face.

**Streaming**: resposta entregue em pedaços, à medida que o modelo gera.

**Vibe coding**: pedir código de forma vaga e aceitar o que vier, sem especificação.

**Workflow**: o processo automatizado, descrito em YAML.

**YAML**: formato de arquivo de configuração, sensível a indentação.
