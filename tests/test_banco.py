"""Testes do cliente do banco, com um banco de mentira (httpx.MockTransport)."""

import httpx
import pytest

from assistente.conhecimento.banco import TAMANHO_DO_LOTE, Banco, ErroDoBanco

CHAVE = "sb_secret_chave-de-mentira-0123456789"


def banco_com(responder):
    transporte = httpx.MockTransport(responder)
    return Banco("https://exemplo.supabase.co", CHAVE, transporte=transporte)


def test_limpar_apaga_so_a_colecao_pedida():
    vistos = []

    def responder(req):
        vistos.append((req.method, req.url.path, dict(req.url.params)))
        return httpx.Response(204)

    banco_com(responder).limpar("teste")
    assert vistos == [("DELETE", "/rest/v1/trechos", {"colecao": "eq.teste"})]


def test_inserir_envia_em_lotes_e_sem_pedir_o_corpo_de_volta():
    lotes = []

    def responder(req):
        assert req.headers["prefer"] == "return=minimal"
        lotes.append(len(req.read().decode().split('"conteudo"')) - 1)
        return httpx.Response(201)

    linhas = [{"conteudo": f"c{i}"} for i in range(TAMANHO_DO_LOTE * 2 + 3)]
    banco_com(responder).inserir(linhas)
    assert lotes == [TAMANHO_DO_LOTE, TAMANHO_DO_LOTE, 3]


def test_a_chave_vai_no_cabecalho_apikey():
    def responder(req):
        assert req.headers["apikey"] == CHAVE
        assert "authorization" not in req.headers  # chave nova não vai no Bearer
        return httpx.Response(204)

    banco_com(responder).limpar("teste")


def test_contar_le_o_total_do_cabecalho_content_range():
    def responder(req):
        assert req.headers["prefer"] == "count=exact"
        cabecalhos = {"content-range": "0-0/162"}
        return httpx.Response(206, headers=cabecalhos, json=[{"id": 1}])

    assert banco_com(responder).contar("teste") == 162


def test_contar_colecao_vazia():
    def responder(_req):
        return httpx.Response(200, headers={"content-range": "*/0"}, json=[])

    assert banco_com(responder).contar("teste") == 0


def test_promover_manda_a_versao_e_devolve_quantos_foram():
    def responder(req):
        assert req.url.path == "/rest/v1/rpc/promover"
        assert req.read() == b'{"p_versao":"abc123"}'
        return httpx.Response(200, json=162)

    assert banco_com(responder).promover("abc123") == 162


def test_promover_versao_errada_vira_erro_com_a_mensagem_do_banco():
    def responder(_req):
        corpo = '{"message":"a colecao teste nao tem a versao x — nada foi promovido"}'
        return httpx.Response(400, text=corpo)

    with pytest.raises(ErroDoBanco, match="nada foi promovido"):
        banco_com(responder).promover("x")


@pytest.mark.parametrize("status", [401, 403])
def test_chave_recusada_diz_para_conferir_a_chave_sem_mostrar_nenhuma(status):
    def responder(_req):
        return httpx.Response(status, json={"message": f"erro com {CHAVE}"})

    with pytest.raises(ErroDoBanco) as erro:
        banco_com(responder).limpar("teste")
    assert "confira se é a chave certa" in str(erro.value)
    assert CHAVE not in str(erro.value)


def test_funcao_inexistente_aponta_para_o_esquema_sql():
    def responder(_req):
        return httpx.Response(404, text="Could not find the function public.promover")

    with pytest.raises(ErroDoBanco, match=r"esquema\.sql"):
        banco_com(responder).promover("x")


def test_banco_fora_do_ar_vira_erro_em_portugues():
    def responder(_req):
        raise httpx.ConnectError("sem rede")

    with pytest.raises(ErroDoBanco, match="não consegui falar com o banco"):
        banco_com(responder).limpar("teste")


def test_erro_do_servidor_traz_um_trecho_curto_da_resposta():
    def responder(_req):
        return httpx.Response(500, text="x" * 1000)

    with pytest.raises(ErroDoBanco) as erro:
        banco_com(responder).limpar("teste")
    assert "HTTP 500" in str(erro.value)
    assert len(str(erro.value)) < 300


def test_chave_antiga_em_jwt_tambem_vai_no_bearer():
    def responder(req):
        assert req.headers["authorization"] == "Bearer eyJabc"
        return httpx.Response(204)

    transporte = httpx.MockTransport(responder)
    Banco("https://x.co", "eyJabc", transporte=transporte).limpar("teste")
