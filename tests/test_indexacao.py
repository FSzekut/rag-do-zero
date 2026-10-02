"""Testes da indexação (RF23) — com um modelo e um banco de mentira.

O que se confere é a **ordem e o conteúdo**: vetoriza antes de apagar, só mexe na
coleção teste, grava a versão em cada linha, e confere a contagem no fim.
"""

import json
from pathlib import Path

import httpx
import pytest

from assistente.config import BaseConhecimento
from assistente.conhecimento.banco import Banco
from assistente.conhecimento.embeddings import (
    DIMENSOES,
    ErroDeEmbedding,
    conferir_dimensoes,
)
from assistente.conhecimento.indexacao import ErroDeIndexacao, indexar

RAIZ = Path(__file__).resolve().parent.parent
BASE = BaseConhecimento()


class ModeloDeMentira:
    """Um vetor determinístico por texto, de 384 posições, e o registro das chamadas."""

    def __init__(self, eventos):
        self.eventos = eventos
        self.textos: list[str] = []

    def vetorizar(self, textos):
        self.eventos.append("vetorizar")
        self.textos += list(textos)
        return [[(len(t) % 7) / 7.0] * DIMENSOES for t in textos]


class BancoDeMentira:
    """Registra o que o banco recebeu, na ordem, e devolve contagens coerentes."""

    def __init__(self, eventos, *, perde_linhas=0):
        self.eventos = eventos
        self.linhas: list[dict] = []
        self.perde_linhas = perde_linhas
        self.http = httpx.MockTransport(self._responder)

    def _responder(self, req: httpx.Request) -> httpx.Response:
        if req.method == "DELETE":
            self.eventos.append(f"apagar {req.url.params['colecao']}")
            self.linhas = []
            return httpx.Response(204)
        if req.method == "POST":
            self.eventos.append("gravar lote")
            self.linhas += json.loads(req.read())
            return httpx.Response(201)
        total = max(len(self.linhas) - self.perde_linhas, 0)
        return httpx.Response(200, headers={"content-range": f"0-0/{total}"}, json=[])

    def banco(self) -> Banco:
        return Banco("https://exemplo.supabase.co", "chave", transporte=self.http)


@pytest.fixture
def cenario():
    eventos: list[str] = []
    return eventos, ModeloDeMentira(eventos), BancoDeMentira(eventos)


def rodar(cenario, pasta=RAIZ / "documentos", versao="abc123", base=BASE):
    _eventos, modelo, falso = cenario
    banco = falso.banco()
    try:
        return indexar(pasta, base, banco, modelo, versao=versao)
    finally:
        banco.fechar()


def test_vetoriza_antes_de_apagar_e_so_apaga_a_colecao_teste(cenario):
    eventos = cenario[0]
    rodar(cenario)
    assert eventos.index("vetorizar") < eventos.index("apagar eq.teste")
    assert [e for e in eventos if e.startswith("apagar")] == ["apagar eq.teste"]
    assert eventos.index("apagar eq.teste") < eventos.index("gravar lote")


def test_cada_linha_leva_colecao_versao_fonte_secao_ordem_e_vetor(cenario):
    rodar(cenario, versao="deadbeef")
    linhas = cenario[2].linhas
    assert linhas and all(linha["colecao"] == "teste" for linha in linhas)
    assert all(linha["versao"] == "deadbeef" for linha in linhas)
    fontes = {linha["fonte"] for linha in linhas}
    assert fontes == {"parte1-cicd-deploy.md", "parte2-rag.md"}
    assert all(len(linha["embedding"]) == DIMENSOES for linha in linhas)
    assert all(linha["conteudo"].strip() for linha in linhas)
    ordens = [linha["ordem"] for linha in linhas if linha["fonte"] == "parte2-rag.md"]
    assert ordens == sorted(ordens)


def test_o_texto_vetorizado_comeca_pelo_titulo_da_secao(cenario):
    rodar(cenario)
    modelo = cenario[1]
    linhas = cenario[2].linhas
    primeira_com_secao = next(linha for linha in linhas if linha["secao"])
    inicio = primeira_com_secao["secao"] + "\n\n"
    assert any(t.startswith(inicio) for t in modelo.textos)


def test_resumo_conta_trechos_e_fontes(cenario):
    resumo = rodar(cenario, versao="abc123")
    assert resumo.trechos == len(cenario[2].linhas)
    assert set(resumo.por_fonte) == {"parte1-cicd-deploy.md", "parte2-rag.md"}
    assert resumo.versao == "abc123"


def test_tamanho_do_trecho_do_config_muda_a_divisao(cenario):
    pequeno = rodar(cenario, base=BaseConhecimento(tamanho_trecho=60))
    cenario[2].linhas.clear()
    grande = rodar(cenario, base=BaseConhecimento(tamanho_trecho=250))
    assert pequeno.trechos > grande.trechos


def test_pasta_com_problema_barra_antes_de_falar_com_o_banco(cenario, tmp_path):
    (tmp_path / "apostila.pdf").write_bytes(b"%PDF")
    with pytest.raises(ErroDeIndexacao, match=r"apostila\.pdf"):
        rodar(cenario, pasta=tmp_path)
    assert cenario[0] == []  # nem o modelo nem o banco foram chamados


def test_contagem_diferente_no_fim_e_erro(cenario):
    falso = BancoDeMentira(cenario[0], perde_linhas=2)
    with pytest.raises(ErroDeIndexacao, match="algo foi perdido"):
        rodar((cenario[0], cenario[1], falso))


def test_se_o_modelo_falha_a_colecao_teste_antiga_fica_intacta():
    eventos: list[str] = []

    class ModeloQueQuebra:
        def vetorizar(self, _textos):
            raise ErroDeEmbedding("o modelo caiu")

    falso = BancoDeMentira(eventos)
    banco = falso.banco()
    with pytest.raises(ErroDeEmbedding):
        indexar(RAIZ / "documentos", BASE, banco, ModeloQueQuebra(), versao="x")
    assert eventos == []  # nada foi apagado


def test_vetor_de_tamanho_errado_e_apanhado_antes_do_banco():
    with pytest.raises(ErroDeEmbedding, match="384"):
        conferir_dimensoes([[0.1] * 10])


def test_vetoriza_em_lotes_para_nao_estourar_a_memoria(cenario):
    chamadas = []
    original = cenario[1].vetorizar

    def espiar(textos):
        chamadas.append(len(textos))
        return original(textos)

    cenario[1].vetorizar = espiar
    rodar(cenario)
    assert len(chamadas) > 1 and max(chamadas) <= 32
