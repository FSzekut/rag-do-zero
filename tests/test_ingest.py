"""Teste da etapa de chunking. Nasce vermelho — é a T2.

Roda sem rede e sem chave: chunking é corte de string, não tem modelo envolvido.
"""

from langchain_core.documents import Document

from rag import config
from rag.ingest import split_documents


def _documento_longo(n_paragrafos: int = 40) -> Document:
    texto = "\n\n".join(
        f"Parágrafo {i} com texto suficiente para forçar o corte em mais de um chunk."
        for i in range(n_paragrafos)
    )
    return Document(page_content=texto, metadata={"source": "fake.md"})


def test_divide_em_mais_de_um_chunk():
    chunks = split_documents([_documento_longo()])
    assert len(chunks) > 1


def test_respeita_o_tamanho_maximo():
    chunks = split_documents([_documento_longo()])
    assert all(len(c.page_content) <= config.CHUNK_SIZE for c in chunks)


def test_preserva_a_origem():
    """Sem isso a resposta final não tem como citar fonte."""
    chunks = split_documents([_documento_longo()])
    assert all(c.metadata.get("source") == "fake.md" for c in chunks)
