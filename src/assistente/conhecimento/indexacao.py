"""Reconstruir a coleção `teste` a partir dos documentos (RF23).

O caminho é sempre o mesmo: conferir a pasta, dividir em trechos, gerar os vetores,
**só então** apagar a coleção `teste` e gravar a nova. A ordem importa: gerar os
vetores é a parte lenta e a que mais falha (modelo, memória); se falhar, a coleção
`teste` antiga continua intacta. E a coleção `producao`, que o assistente no ar
consulta, **nunca é tocada aqui**.

Cada linha leva a `versao` (o hash do commit), que é o que deixa `promover` recusar
um índice que não seja o do commit que está sendo publicado.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..config import BaseConhecimento
from .banco import Banco
from .documentos import verificar_pasta
from .embeddings import Embeddador, conferir_dimensoes
from .trechos import Trecho, dividir_pasta

TAMANHO_DO_LOTE_DE_VETORES = 32


class ErroDeIndexacao(Exception):
    """A indexação não pôde ser feita, com o motivo em português."""


@dataclass(frozen=True)
class Resumo:
    versao: str
    trechos: int
    por_fonte: dict[str, int]
    segundos: float


def _linha(trecho: Trecho, vetor: list[float], versao: str) -> dict:
    return {
        "colecao": "teste",
        "versao": versao,
        "fonte": trecho.fonte,
        "secao": trecho.secao,
        "ordem": trecho.ordem,
        "conteudo": trecho.conteudo,
        "embedding": vetor,
    }


def indexar(
    pasta: Path,
    base: BaseConhecimento,
    banco: Banco,
    embeddador: Embeddador,
    *,
    versao: str,
    registrar: Callable[[str], None] = lambda _mensagem: None,
) -> Resumo:
    """Reconstrói a coleção `teste`. Devolve o resumo do que foi gravado."""
    inicio = time.monotonic()

    problemas = verificar_pasta(pasta)
    if problemas:
        raise ErroDeIndexacao(
            "a pasta de documentos tem problemas:\n  - " + "\n  - ".join(problemas)
        )

    trechos = dividir_pasta(
        pasta, tamanho=base.tamanho_trecho, sobreposicao=base.sobreposicao_trecho
    )
    if not trechos:
        raise ErroDeIndexacao("os documentos não geraram nenhum trecho")
    registrar(f"{len(trechos)} trechos (até {base.tamanho_trecho} palavras cada)")

    vetores: list[list[float]] = []
    for i in range(0, len(trechos), TAMANHO_DO_LOTE_DE_VETORES):
        lote = trechos[i : i + TAMANHO_DO_LOTE_DE_VETORES]
        vetores += embeddador.vetorizar([t.texto_para_embedding for t in lote])
        registrar(f"vetores: {min(i + len(lote), len(trechos))}/{len(trechos)}")
    conferir_dimensoes(vetores)

    banco.limpar("teste")
    banco.inserir([_linha(t, v, versao) for t, v in zip(trechos, vetores, strict=True)])

    gravados = banco.contar("teste")
    if gravados != len(trechos):
        raise ErroDeIndexacao(
            f"gravei {len(trechos)} trechos mas o banco tem {gravados} na coleção "
            "teste: algo foi perdido no caminho"
        )

    por_fonte: dict[str, int] = {}
    for t in trechos:
        por_fonte[t.fonte] = por_fonte.get(t.fonte, 0) + 1
    return Resumo(versao, len(trechos), por_fonte, time.monotonic() - inicio)
