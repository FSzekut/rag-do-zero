# Tasks — rag_do_zero

Ordem sugerida. Cada uma fecha com um commit que roda.

- [ ] **T0 — ambiente**: `uv venv`, torch CPU-only, `uv pip install -r requirements.txt`,
      `git init` e primeiro commit já com o `requirements.txt` dentro
- [ ] **T1 — carga**: `ingest.load_documents()` lê `.pdf/.md/.txt` de `data/raw/` e
      devolve `Document`s com `metadata["source"]` preenchido
- [ ] **T2 — chunking**: `ingest.split_documents()` com `RecursiveCharacterTextSplitter`;
      fazer `tests/test_ingest.py` passar (está vermelho de propósito)
- [ ] **T3 — índice**: `index.build_index()` grava o Chroma em `outputs/chroma/`;
      `index.load_index()` reabre sem recalcular embedding
- [ ] **T4 — busca**: `retrieve.search()` devolve trechos + score; olhar os scores
      antes de seguir — é aqui que se descobre se o chunking prestou
- [ ] **T5 — resposta**: `answer.answer()` monta o prompt com os trechos, chama o
      Claude e devolve resposta + fontes
- [ ] **T6 — fecho**: rodar as duas perguntas de teste, anotar no README o que
      funcionou e o que não, e commitar

## Depois (não agora)

Avaliação com perguntas de referência · reranking · chunking por seção em vez de
por caractere · comparar MiniLM com um modelo de embedding maior.
