"""Provar o que cada chave do Supabase pode e não pode fazer (RF35).

"O banco impede" só vale se alguém **tenta** fazer a coisa proibida. Este módulo
tenta, com as duas chaves, e compara com o esperado:

- a chave **publicável** (a do Space) só pode chamar `buscar_producao` e
  `contar_producao`. Ler a tabela, gravar, apagar, ver a coleção `teste` ou
  promover o índice tem que ser **recusado**;
- a chave **secreta** (a do GitHub Actions) pode tudo isso.

Roda de novo sempre que o `esquema.sql` mudar. Não imprime chave nenhuma.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

VETOR_UNITARIO = "[" + ",".join(["1"] + ["0"] * 383) + "]"  # 384 posições
CORPO_DA_BUSCA = {"p_pergunta": "teste", "p_vetor": VETOR_UNITARIO, "p_n": 4}


@dataclass(frozen=True)
class Verificacao:
    quem: str  # "publicável" ou "secreta"
    o_que: str
    esperado: str  # "recusado" ou "permitido"
    status: int | None
    ok: bool
    dica: str = ""


def _cabecalhos(chave: str) -> dict[str, str]:
    cabecalhos = {"apikey": chave, "Content-Type": "application/json"}
    if chave.startswith("eyJ"):  # chave antiga, em formato JWT, também vai no Bearer
        cabecalhos["Authorization"] = f"Bearer {chave}"
    return cabecalhos


def _avaliar(esperado: str, resposta: httpx.Response) -> tuple[bool, str]:
    status = resposta.status_code
    if status == 404 and "function" in resposta.text.lower():
        return False, "a função não existe: o esquema.sql foi rodado neste projeto?"
    if esperado == "recusado":
        if status in (401, 403):
            return True, ""
        return False, "era para ser RECUSADO e não foi: permissão aberta demais"
    if esperado == "permitido":
        if status == 200:
            return True, ""
        if status in (401, 403):
            return False, "era para funcionar e foi recusado: confira a chave"
        return False, f"resposta inesperada: {resposta.text[:120]}"
    # "chamavel": a função existe e rodou, mas recusa de propósito um commit que não é
    # o da coleção teste (é o que a torna segura de testar: nunca muda nada)
    if status == 400 and "nada foi promovido" in resposta.text:
        return True, ""
    return False, f"resposta inesperada ({status}): {resposta.text[:120]}"


def _tentar(
    cliente: httpx.Client, quem: str, o_que: str, esperado: str,
    metodo: str, caminho: str, corpo: dict | None = None,
) -> Verificacao:
    try:
        resposta = cliente.request(metodo, caminho, json=corpo)
    except httpx.HTTPError as erro:
        return Verificacao(quem, o_que, esperado, None, False,
                           f"não consegui falar com o banco: {type(erro).__name__}")
    ok, dica = _avaliar(esperado, resposta)
    return Verificacao(quem, o_que, esperado, resposta.status_code, ok, dica)


def verificar(
    url: str,
    chave_publicavel: str,
    chave_secreta: str,
    *,
    transporte: httpx.BaseTransport | None = None,
) -> list[Verificacao]:
    """Faz as tentativas com as duas chaves e devolve o resultado de cada uma."""
    base = url.rstrip("/")
    resultados: list[Verificacao] = []

    with httpx.Client(base_url=base, headers=_cabecalhos(chave_publicavel),
                      timeout=30, transport=transporte) as pub:
        quem = "publicável"
        resultados += [
            _tentar(pub, quem, "ler a tabela trechos direto", "recusado",
                    "GET", "/rest/v1/trechos?select=id&limit=1"),
            _tentar(pub, quem, "gravar na tabela trechos", "recusado",
                    "POST", "/rest/v1/trechos",
                    {"colecao": "teste", "versao": "x", "fonte": "x", "ordem": 0}),
            _tentar(pub, quem, "apagar da tabela trechos", "recusado",
                    "DELETE", "/rest/v1/trechos?id=gt.0"),
            _tentar(pub, quem, "buscar na coleção teste", "recusado",
                    "POST", "/rest/v1/rpc/buscar_teste", CORPO_DA_BUSCA),
            _tentar(pub, quem, "promover o índice", "recusado",
                    "POST", "/rest/v1/rpc/promover", {"p_versao": "verificacao"}),
            _tentar(pub, quem, "chamar a busca interna", "recusado",
                    "POST", "/rest/v1/rpc/busca_interna",
                    {"p_colecao": "teste", **CORPO_DA_BUSCA,
                     "p_peso_palavras": 1, "p_peso_sentido": 1, "p_sim_min": 0}),
            _tentar(pub, quem, "buscar na coleção producao (o que o app faz)",
                    "permitido", "POST", "/rest/v1/rpc/buscar_producao",
                    CORPO_DA_BUSCA),
            _tentar(pub, quem, "contar os trechos da producao (o log do app)",
                    "permitido", "POST", "/rest/v1/rpc/contar_producao", {}),
        ]

    with httpx.Client(base_url=base, headers=_cabecalhos(chave_secreta),
                      timeout=30, transport=transporte) as sec:
        quem = "secreta"
        resultados += [
            _tentar(sec, quem, "ler a tabela trechos direto", "permitido",
                    "GET", "/rest/v1/trechos?select=id&limit=1"),
            _tentar(sec, quem, "buscar na coleção teste", "permitido",
                    "POST", "/rest/v1/rpc/buscar_teste", CORPO_DA_BUSCA),
            _tentar(sec, quem, "buscar na coleção producao", "permitido",
                    "POST", "/rest/v1/rpc/buscar_producao", CORPO_DA_BUSCA),
            _tentar(sec, quem, "chamar promover (versão inexistente: não muda nada)",
                    "chamavel", "POST", "/rest/v1/rpc/promover",
                    {"p_versao": "verificacao"}),
        ]
    return resultados
