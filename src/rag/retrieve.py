"""Etapa 4: dada uma pergunta, achar os trechos mais próximos.

T4 — search
    similarity_search_with_score devolve (Document, score) — prefira essa forma à
    versão sem score. O score é o termômetro do chunking: se os melhores trechos
    de uma pergunta óbvia vêm com score ruim, o problema está lá atrás, no corte,
    não no prompt.

    Atenção: no Chroma o score é *distância* — menor é melhor. Não inverta.
"""

from __future__ import annotations

from langchain_core.documents import Document

from . import config


def search(question: str, k: int | None = None) -> list[tuple[Document, float]]:
    """Retorna os `k` trechos mais próximos da pergunta, com o score de cada um."""
    raise NotImplementedError("T4")
