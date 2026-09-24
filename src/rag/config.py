"""Configuração central: caminhos e parâmetros do pipeline.

Tudo que o resto do código precisa saber sobre "onde" e "com quais números"
mora aqui. Nenhum outro módulo monta caminho na mão.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Raiz do projeto: este arquivo está em <raiz>/src/rag/config.py
ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "outputs"
CHROMA_DIR = OUTPUT_DIR / "chroma"

# Modelo de geração. Trocar por claude-sonnet-5 se quiser rodar mais barato.
MODEL = os.getenv("RAG_MODEL", "claude-opus-5")
MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "2000"))

# Embedding local: roda na CPU, sem chave e sem custo por chunk.
EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
TOP_K = int(os.getenv("RAG_TOP_K", "4"))

COLLECTION = os.getenv("RAG_COLLECTION", "rag_do_zero")

SUPPORTED_SUFFIXES = {".pdf", ".md", ".txt"}
