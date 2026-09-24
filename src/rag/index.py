"""Etapa 3: transformar chunks em vetores e guardar num Chroma persistido.

T3 — build_index
    Cria o embedding (HuggingFaceEmbeddings com config.EMBEDDING_MODEL) e grava
    os chunks num Chroma apontando para config.CHROMA_DIR, coleção
    config.COLLECTION. A primeira execução baixa o modelo de embedding: demora.

T3 — load_index
    Reabre o mesmo diretório sem recalcular nada. É o que separa "indexei uma
    vez" de "reindexo a cada pergunta".

Detalhe que costuma morder: o objeto de embedding usado na leitura tem que ser o
mesmo da escrita. Vetor de modelo A não conversa com vetor de modelo B.
"""

from __future__ import annotations

from langchain_core.documents import Document

from . import config


def build_index(chunks: list[Document]):
    """Cria (ou recria) o índice vetorial em config.CHROMA_DIR."""
    raise NotImplementedError("T3")


def load_index():
    """Abre o índice já gravado em disco."""
    raise NotImplementedError("T3")
