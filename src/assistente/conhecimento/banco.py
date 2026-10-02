"""O cliente do banco (Supabase), pela API REST (PostgREST).

Usa `httpx`, que já vem instalado com o Gradio e o OpenAI: sem o SDK do Supabase,
são duas dependências a menos no Space.

Este cliente serve a **dois tipos de chave**, e quem decide qual usar é quem o cria:
o pipeline usa a **secreta** (grava), o app usa a **publicável** (só lê). O que cada
chave consegue fazer não depende deste código: quem decide é o banco, pelas
permissões do `esquema.sql` (e `scripts/verificar_banco.py` prova isso).

Nenhuma mensagem de erro daqui contém a chave.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

TAMANHO_DO_LOTE = 20  # linhas por envio: cada vetor tem 384 números


class ErroDoBanco(Exception):
    """Falha ao falar com o banco, em português e sem segredo na mensagem."""


def _cabecalhos(chave: str) -> dict[str, str]:
    cabecalhos = {"apikey": chave, "Content-Type": "application/json"}
    if chave.startswith("eyJ"):  # chave antiga, em formato JWT, também vai no Bearer
        cabecalhos["Authorization"] = f"Bearer {chave}"
    return cabecalhos


def _explicar(resposta: httpx.Response, o_que: str) -> ErroDoBanco:
    """Traduz uma resposta de erro, sem repetir nada que possa ser segredo."""
    status = resposta.status_code
    if status in (401, 403):
        return ErroDoBanco(
            f"o banco recusou a chave ao {o_que} (HTTP {status}): "
            "confira se é a chave certa para esta operação"
        )
    if status == 404 and "function" in resposta.text.lower():
        return ErroDoBanco(
            f"a função do banco não existe ao {o_que}: "
            "o supabase/esquema.sql foi rodado neste projeto?"
        )
    trecho = " ".join(resposta.text.split())[:200]
    return ErroDoBanco(f"o banco respondeu HTTP {status} ao {o_que}: {trecho}")


class Banco:
    def __init__(
        self,
        url: str,
        chave: str,
        *,
        transporte: httpx.BaseTransport | None = None,
        tempo_limite: float = 60,
    ) -> None:
        self._http = httpx.Client(
            base_url=url.rstrip("/"),
            headers=_cabecalhos(chave),
            timeout=tempo_limite,
            transport=transporte,
        )

    def _pedir(
        self, o_que: str, metodo: str, caminho: str, **opcoes: Any
    ) -> httpx.Response:
        try:
            resposta = self._http.request(metodo, caminho, **opcoes)
        except httpx.HTTPError as erro:
            raise ErroDoBanco(
                f"não consegui falar com o banco ao {o_que}: {type(erro).__name__}"
            ) from erro
        if resposta.status_code >= 400:
            raise _explicar(resposta, o_que)
        return resposta

    # -- escrita (só a chave secreta consegue) --------------------------------------

    def limpar(self, colecao: str) -> None:
        """Apaga todos os trechos de uma coleção."""
        self._pedir(
            f"limpar a coleção {colecao}", "DELETE", "/rest/v1/trechos",
            params={"colecao": f"eq.{colecao}"},
        )

    def inserir(self, linhas: Sequence[dict[str, Any]]) -> None:
        """Grava as linhas, em lotes."""
        for inicio in range(0, len(linhas), TAMANHO_DO_LOTE):
            lote = list(linhas[inicio : inicio + TAMANHO_DO_LOTE])
            self._pedir(
                "gravar trechos", "POST", "/rest/v1/trechos",
                json=lote, headers={"Prefer": "return=minimal"},
            )

    def promover(self, versao: str) -> int:
        """Troca o índice no ar pelo avaliado. Devolve quantos trechos foram."""
        resposta = self._pedir(
            "promover o índice", "POST", "/rest/v1/rpc/promover",
            json={"p_versao": versao},
        )
        return int(resposta.json())

    # -- leitura ---------------------------------------------------------------------

    def contar(self, colecao: str) -> int:
        """Quantos trechos há numa coleção (pela chave secreta)."""
        resposta = self._pedir(
            f"contar a coleção {colecao}", "GET", "/rest/v1/trechos",
            params={"select": "id", "colecao": f"eq.{colecao}"},
            headers={"Prefer": "count=exact", "Range": "0-0"},
        )
        total = resposta.headers.get("content-range", "").rsplit("/", 1)[-1]
        if not total.isdigit():
            raise ErroDoBanco("o banco não informou a contagem de trechos")
        return int(total)

    def fechar(self) -> None:
        self._http.close()
