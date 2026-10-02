"""Transformar texto em vetor (RF21 e RF22).

O modelo é **fixo**: `paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensões, rodando
na CPU pela biblioteca `fastembed`, sem chave de API. Os trechos são vetorizados na
indexação e a pergunta é vetorizada na consulta, **com o mesmo modelo**: vetores de
modelos diferentes vivem em "mapas" diferentes e a comparação não faz sentido. Por
isso o nome do modelo é uma constante do código, não um campo do config.

Um limite que moldou o projeto, medido em 01/10/2026: o tokenizador deste modelo
**corta em 128 tokens** (o modelo foi treinado assim). Com texto em português isso
dá cerca de 60 palavras. O que passa disso continua valendo para a busca por
palavras e para o modelo de linguagem, mas **não entra no vetor**.

O `fastembed` é importado só na hora de usar: o resto do app, e os testes, não
precisam dele instalado nem do modelo baixado (cerca de 250 MB, na primeira vez).
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

NOME_DO_MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIMENSOES = 384
LIMITE_DE_TOKENS = 128
CASAS_DECIMAIS = 6  # a precisão que sobra já é mais que o modelo tem; encolhe o envio


class ErroDeEmbedding(Exception):
    """O modelo não carregou, ou devolveu um vetor do tamanho errado."""


class Embeddador(Protocol):
    """O mínimo que a indexação e a busca precisam saber sobre o modelo.

    É o que permite testar tudo sem baixar o modelo: nos testes entra um dublê.
    """

    def vetorizar(self, textos: Sequence[str]) -> list[list[float]]: ...


def _pasta_do_cache() -> str:
    """Onde o modelo fica guardado, para não baixar de novo a cada execução."""
    return os.environ.get("FASTEMBED_CACHE_PATH") or str(
        Path.home() / ".cache" / "fastembed"
    )


class EmbeddadorFastembed:
    """O modelo de verdade. Carrega só na primeira vez que for usado."""

    def __init__(self, pasta_do_cache: str | None = None) -> None:
        self._pasta = pasta_do_cache or _pasta_do_cache()
        self._modelo = None

    def _carregar(self):
        if self._modelo is None:
            try:
                from fastembed import TextEmbedding

                self._modelo = TextEmbedding(NOME_DO_MODELO, cache_dir=self._pasta)
            except ImportError as erro:
                raise ErroDeEmbedding(
                    "a biblioteca fastembed não está instalada: "
                    "rode `uv pip install fastembed`"
                ) from erro
            except Exception as erro:  # download, disco, formato do cache
                raise ErroDeEmbedding(
                    f"não consegui carregar o modelo {NOME_DO_MODELO}: "
                    f"{type(erro).__name__}"
                ) from erro
        return self._modelo

    def vetorizar(self, textos: Sequence[str]) -> list[list[float]]:
        if not textos:
            return []
        modelo = self._carregar()
        vetores = [
            [round(float(x), CASAS_DECIMAIS) for x in v]
            for v in modelo.embed(list(textos))
        ]
        conferir_dimensoes(vetores)
        return vetores


def conferir_dimensoes(vetores: Sequence[Sequence[float]]) -> None:
    """Um vetor de tamanho errado só estouraria no banco, longe da causa."""
    for i, vetor in enumerate(vetores):
        if len(vetor) != DIMENSOES:
            raise ErroDeEmbedding(
                f"o vetor {i} tem {len(vetor)} dimensões e o banco espera "
                f"{DIMENSOES}: o modelo de embedding foi trocado?"
            )
