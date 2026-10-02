"""Testes do modelo de embedding.

O modelo de verdade pesa cerca de 250 MB e leva alguns segundos para carregar, então
o teste dele só roda quando pedido:
`RODAR_MODELO_REAL=1 pytest tests/test_embeddings.py`.
O CI comum não baixa modelo nenhum.
"""

import math
import os

import pytest

from assistente.conhecimento.embeddings import (
    DIMENSOES,
    LIMITE_DE_TOKENS,
    NOME_DO_MODELO,
    EmbeddadorFastembed,
    ErroDeEmbedding,
)


def cosseno(a, b):
    produto = sum(x * y for x, y in zip(a, b, strict=True))
    return produto / (math.hypot(*a) * math.hypot(*b))


def test_constantes_batem_com_a_spec():
    assert NOME_DO_MODELO.endswith("paraphrase-multilingual-MiniLM-L12-v2")
    assert (DIMENSOES, LIMITE_DE_TOKENS) == (384, 128)


def test_lista_vazia_nao_carrega_o_modelo():
    modelo = EmbeddadorFastembed(pasta_do_cache="/nao/existe")
    assert modelo.vetorizar([]) == []


def test_sem_o_modelo_o_erro_e_em_portugues(tmp_path, monkeypatch):
    import builtins

    real = builtins.__import__

    def sem_fastembed(nome, *args, **kwargs):
        if nome == "fastembed":
            raise ImportError("sem fastembed")
        return real(nome, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", sem_fastembed)
    with pytest.raises(ErroDeEmbedding, match="fastembed não está instalada"):
        EmbeddadorFastembed(pasta_do_cache=str(tmp_path)).vetorizar(["oi"])


@pytest.mark.skipif(
    not os.environ.get("RODAR_MODELO_REAL"),
    reason="baixa o modelo (250 MB): sob demanda",
)
class TestModeloDeVerdade:
    @pytest.fixture(scope="class")
    def modelo(self):
        return EmbeddadorFastembed()

    def test_devolve_vetores_de_384_posicoes(self, modelo):
        vetores = modelo.vetorizar(["onde ficam as chaves?", "outra frase"])
        assert [len(v) for v in vetores] == [DIMENSOES, DIMENSOES]

    def test_e_deterministico(self, modelo):
        assert modelo.vetorizar(["mesma frase"]) == modelo.vetorizar(["mesma frase"])

    def test_parafrase_fica_mais_perto_que_assunto_diferente(self, modelo):
        base, parafrase, outro = modelo.vetorizar([
            "Onde eu guardo a credencial do modelo?",
            "Em que lugar cadastro a chave de API?",
            "A colheita da soja começa em setembro.",
        ])
        assert cosseno(base, parafrase) > cosseno(base, outro) + 0.15

    def test_pergunta_em_ingles_acha_texto_em_portugues(self, modelo):
        pergunta, certo, errado = modelo.vetorizar([
            "where do I store the API key?",
            "A chave de API fica nos secrets do Space, nunca no repositório.",
            "A safra de soja foi recorde neste ano.",
        ])
        assert cosseno(pergunta, certo) > cosseno(pergunta, errado)

    def test_texto_alem_de_128_tokens_nao_muda_o_vetor(self, modelo):
        # a base já passa dos 128 tokens: o que vem depois é cortado e não conta
        base = "palavra " * 200
        com_cauda_diferente = base + "completamente diferente " * 100
        a, b = modelo.vetorizar([base, com_cauda_diferente])
        assert cosseno(a, b) > 0.99
