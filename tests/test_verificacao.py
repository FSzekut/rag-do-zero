"""Testes da verificação de permissões do banco — com um banco de mentira.

Dois bancos falsos: um que se comporta como o `esquema.sql` manda, e outro com a
permissão aberta demais. A verificação tem que aprovar o primeiro e reprovar o
segundo, apontando exatamente o que vazou.
"""

import httpx

from assistente.conhecimento.verificacao import verificar

PUBLICAVEL = "chave-publicavel-de-mentira"
SECRETA = "chave-secreta-de-mentira"


def banco(*, vaza_tabela_para_publicavel=False, sem_funcoes=False):
    def responder(requisicao: httpx.Request) -> httpx.Response:
        chave = requisicao.headers["apikey"]
        caminho = requisicao.url.path
        publicavel = chave == PUBLICAVEL
        if sem_funcoes and "/rpc/" in caminho:
            return httpx.Response(404, text="Could not find the function public.x")
        if caminho == "/rest/v1/trechos":
            if publicavel and not vaza_tabela_para_publicavel:
                return httpx.Response(401, json={"code": "42501"})
            return httpx.Response(200, json=[])
        if "/rpc/" in caminho:
            funcao = caminho.rsplit("/", 1)[1]
            if publicavel and funcao not in ("buscar_producao", "contar_producao"):
                return httpx.Response(401, json={"code": "42501"})
            if funcao == "promover":
                return httpx.Response(400, text='{"message":"nada foi promovido"}')
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    return httpx.MockTransport(responder)


def rodar(**opcoes):
    return verificar(
        "https://exemplo.supabase.co", PUBLICAVEL, SECRETA,
        transporte=banco(**opcoes),
    )


def test_banco_como_a_spec_manda_passa_em_tudo():
    resultados = rodar()
    assert resultados and all(r.ok for r in resultados)
    assert {r.quem for r in resultados} == {"publicável", "secreta"}


def test_a_chave_publicavel_e_testada_nas_seis_coisas_proibidas():
    publicaveis = [r for r in rodar() if r.quem == "publicável"]
    proibidas = [r for r in publicaveis if r.esperado == "recusado"]
    assert len(proibidas) == 6
    assert {r.status for r in proibidas} == {401}


def test_tabela_aberta_para_a_chave_publicavel_e_apanhada():
    ruins = [r for r in rodar(vaza_tabela_para_publicavel=True) if not r.ok]
    assert {r.o_que for r in ruins} == {
        "ler a tabela trechos direto",
        "gravar na tabela trechos",
        "apagar da tabela trechos",
    }
    assert all("RECUSADO" in r.dica for r in ruins)


def test_esquema_nao_rodado_diz_o_que_fazer():
    ruins = [r for r in rodar(sem_funcoes=True) if not r.ok]
    assert ruins
    assert any("esquema.sql" in r.dica for r in ruins)


def test_banco_fora_do_ar_nao_derruba_a_verificacao():
    def cair(_requisicao):
        raise httpx.ConnectError("sem rede")

    resultados = verificar(
        "https://exemplo.supabase.co", PUBLICAVEL, SECRETA,
        transporte=httpx.MockTransport(cair),
    )
    assert resultados and not any(r.ok for r in resultados)
    assert all(r.status is None for r in resultados)


def test_nenhuma_chave_aparece_no_resultado():
    texto = repr(rodar(vaza_tabela_para_publicavel=True))
    assert PUBLICAVEL not in texto and SECRETA not in texto


def test_chave_antiga_em_jwt_tambem_vai_no_bearer():
    vistos = []

    def espiar(requisicao):
        vistos.append(requisicao.headers.get("authorization"))
        return httpx.Response(401)

    verificar("https://x.co", "eyJ-publicavel", "eyJ-secreta",
              transporte=httpx.MockTransport(espiar))
    assert "Bearer eyJ-publicavel" in vistos
