"""Etapa 5: montar o prompt com os trechos recuperados e responder.

T5 — format_context
    Numera os trechos e marca a origem de cada um ([1] arquivo.pdf, p. 3), para
    o modelo ter como citar e você ter como conferir.

T5 — answer
    ChatAnthropic (langchain_anthropic) com config.MODEL e config.MAX_TOKENS.
    A chave vem de ANTHROPIC_API_KEY no .env.

    Duas regras que o prompt precisa carregar, e que são metade da nota deste
    projeto:
      1. responder SÓ com o que está nos trechos;
      2. quando os trechos não contiverem a resposta, dizer que não sabe —
         inventar com convicção é o modo de falha clássico de RAG.
"""

from __future__ import annotations

from langchain_core.documents import Document

from . import config

SYSTEM_PROMPT = """Você responde perguntas usando apenas os trechos fornecidos.
Se os trechos não contiverem a resposta, diga que não encontrou.
Cite o número do trecho que sustenta cada afirmação."""


def format_context(hits: list[tuple[Document, float]]) -> str:
    """Formata os trechos recuperados como contexto numerado e rastreável."""
    raise NotImplementedError("T5")


def answer(question: str) -> tuple[str, list[Document]]:
    """Responde a pergunta e devolve também os trechos que sustentaram a resposta."""
    raise NotImplementedError("T5")
