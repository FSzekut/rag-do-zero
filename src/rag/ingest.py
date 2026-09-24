"""Etapa 1 e 2 do pipeline: carregar os arquivos e cortar em chunks.

T1 — load_documents
    Varre config.RAW_DIR, aceita apenas config.SUPPORTED_SUFFIXES e devolve uma
    lista de Document. Cada Document precisa sair daqui com
    metadata["source"] = caminho relativo do arquivo, senão a citação da
    resposta final não tem de onde vir.

    Carregadores prontos que servem: PyPDFLoader (pdf, um Document por página,
    já traz metadata["page"]) e TextLoader (md e txt).

T2 — split_documents
    RecursiveCharacterTextSplitter com config.CHUNK_SIZE e config.CHUNK_OVERLAP.
    O splitter preserva o metadata do Document de origem — confirme isso, é o
    que mantém a citação viva depois do corte.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from . import config


def load_documents(raw_dir: Path | None = None) -> list[Document]:
    """Lê os arquivos suportados de `raw_dir` (default: config.RAW_DIR)."""
    raise NotImplementedError("T1")


def split_documents(documents: list[Document]) -> list[Document]:
    """Corta os documentos em chunks com overlap."""
    raise NotImplementedError("T2")
