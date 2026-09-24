# rag_do_zero

RAG construído peça por peça — pós **Engenharia de Dados e IA** (Anhanguera).

O RAGnaldo já responde perguntas em produção. Este projeto existe para saber o que
acontece **dentro** dele: carga, chunking, embedding, busca vetorial e prompt, cada
etapa num módulo separado, escrita à mão.

- O combinado está em [`docs/spec.md`](docs/spec.md) — ler antes de codar.
- A ordem do trabalho está em [`docs/tasks.md`](docs/tasks.md).

## Estrutura

```text
src/rag/
  config.py     caminhos e parâmetros    (pronto)
  ingest.py     carga + chunking         T1, T2
  index.py      embedding + Chroma       T3
  retrieve.py   busca vetorial           T4
  answer.py     prompt + Claude          T5
  cli.py        ingest / ask             (pronto)
tests/          teste de chunking, vermelho de propósito
data/raw/       o corpus — fora do git
outputs/chroma/ o índice — gerado, descartável, fora do git
```

## Ambiente

```bash
cd ~/projects/Eng_dados_ia/rag_do_zero
uv venv
source .venv/bin/activate
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install -r requirements.txt
cp .env.example .env    # e preencher ANTHROPIC_API_KEY
```

O torch CPU-only vem antes de propósito: instalado pelo caminho normal, o
`sentence-transformers` puxa alguns GB de CUDA que não servem para nada aqui.

## Uso

```bash
# coloque uns PDFs em data/raw/ primeiro
python -m rag.cli ingest
python -m rag.cli ask "sua pergunta"
pytest
```

## Diário de bordo

Anotar aqui, por etapa, o que surpreendeu — não o que deu certo.

| Etapa | O que aprendi |
|---|---|
| | |
