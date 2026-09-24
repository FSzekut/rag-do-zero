# Spec — rag_do_zero

Escrita antes do código, curta de propósito. Se algo aqui estiver errado, corrigir
**aqui** primeiro e só depois mexer no código.

## Problema

Construir um RAG inteiro à mão, entendendo cada etapa, em vez de chamar uma
`RetrievalQA` pronta. O RAGnaldo já responde perguntas em produção; este projeto
existe para **saber o que acontece dentro dele**.

## Escopo

Um CLI local que:

1. lê documentos de `data/raw/` (`.pdf`, `.md`, `.txt`);
2. divide em chunks com overlap;
3. gera embeddings locais e grava num Chroma persistido em `outputs/chroma/`;
4. dada uma pergunta, recupera os `k` chunks mais próximos;
5. monta um prompt com esses trechos e responde com o Claude, **citando a fonte**
   (arquivo + página/posição) de cada trecho usado.

## Fora de escopo

Interface web, API HTTP, reranking, query rewriting, avaliação automatizada.
Cada um desses é um passo 2 possível, não parte da primeira versão.

## Decisões tomadas

| Decisão | Escolha | Por quê |
|---|---|---|
| Framework | LangChain | é o que aparece na grade e no mercado; aqui usado só como peça, não como piloto automático |
| Vector store | Chroma persistido em disco | roda local, sem serviço externo, e o índice sobrevive entre execuções |
| Embeddings | `all-MiniLM-L6-v2` local | sem chave, sem custo por chunk, e o reindex é livre |
| LLM | Claude (`claude-opus-5`) via `langchain-anthropic` | é a chave que já existe aqui |
| Saída gerada | `outputs/` | regra da casa: nada gerado na raiz, e `outputs/` é descartável |

## Critérios de pronto

- [ ] `python -m rag.cli ingest` roda sobre uma pasta com ao menos 2 arquivos e
      informa quantos documentos e quantos chunks entraram no índice
- [ ] `python -m rag.cli ask "pergunta"` responde usando os trechos recuperados
- [ ] a resposta lista as fontes; nenhuma resposta sai sem fonte
- [ ] quando nada relevante é recuperado, o sistema diz que não sabe em vez de inventar
- [ ] `pytest` passa, e a etapa de chunking tem teste que roda sem rede

## Pergunta em aberto

Qual corpus usar em `data/raw/`? O PPC da pós é candidato óbvio, mas qualquer
conjunto de PDFs serve para a primeira iteração.
