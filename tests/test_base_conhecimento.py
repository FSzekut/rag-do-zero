"""Testes do bloco `base_conhecimento` — verificação T15 da spec da parte 2.

Mesmo padrão de `test_config.py`: parte-se da configuração válida, muda-se uma
coisa, e confere-se o resultado. O bloco é opcional (RF33): sem ele, nada muda.
"""

from pathlib import Path

import pytest
import yaml

from assistente.config import (
    BaseConhecimento,
    ErroDeConfiguracao,
    carregar,
    interpretar,
)

EXEMPLOS = Path(__file__).parent / "exemplos"
RAIZ_DO_PROJETO = Path(__file__).parent.parent


def config_base() -> dict:
    return yaml.safe_load((EXEMPLOS / "config_valido.yaml").read_text(encoding="utf-8"))


def com_base(**campos) -> dict:
    dados = config_base()
    dados["base_conhecimento"] = campos
    return dados


def erros_de(dados: dict) -> str:
    with pytest.raises(ErroDeConfiguracao) as capturado:
        interpretar(dados, raiz=RAIZ_DO_PROJETO)
    return " | ".join(capturado.value.erros)


# --- o bloco é opcional (RF33) ------------------------------------------------


def test_t15_sem_o_bloco_a_base_fica_desligada():
    config = interpretar(config_base(), raiz=RAIZ_DO_PROJETO)
    assert config.base_conhecimento is None


def test_t15_bloco_vazio_liga_a_base_com_os_padroes():
    dados = config_base()
    dados["base_conhecimento"] = None  # "base_conhecimento:" sem nada embaixo
    config = interpretar(dados, raiz=RAIZ_DO_PROJETO)
    assert config.base_conhecimento == BaseConhecimento()


def test_t15_padroes_batem_com_a_spec():
    base = BaseConhecimento()
    assert (base.trechos_por_resposta, base.tamanho_trecho) == (4, 150)
    assert (base.sobreposicao_trecho, base.similaridade_minima) == (15, 0.30)
    assert (base.peso_palavras, base.peso_sentido) == (1.0, 1.0)


def test_t15_bloco_completo_carrega_cada_valor():
    config = interpretar(
        com_base(
            trechos_por_resposta=6, tamanho_trecho=200, sobreposicao_trecho=10,
            peso_palavras=2, peso_sentido=0.5, similaridade_minima=0.4,
        ),
        raiz=RAIZ_DO_PROJETO,
    )
    assert config.base_conhecimento == BaseConhecimento(6, 200, 10, 2.0, 0.5, 0.4)


def test_t15_campo_omitido_vale_o_padrao():
    config = interpretar(com_base(tamanho_trecho=90), raiz=RAIZ_DO_PROJETO)
    assert config.base_conhecimento.tamanho_trecho == 90
    assert config.base_conhecimento.trechos_por_resposta == 4


def test_t15_config_do_projeto_tem_a_base_ligada():
    config = carregar(RAIZ_DO_PROJETO / "config.yaml")
    assert config.base_conhecimento is not None


# --- valores fora do domínio são rejeitados -----------------------------------


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("trechos_por_resposta", 0), ("trechos_por_resposta", 11),
        ("tamanho_trecho", 39), ("tamanho_trecho", 401),
        ("sobreposicao_trecho", -1), ("sobreposicao_trecho", 31),
        ("peso_palavras", -0.1), ("peso_palavras", 5.1),
        ("peso_sentido", -1), ("peso_sentido", 6),
        ("similaridade_minima", -0.1), ("similaridade_minima", 1.1),
    ],
)
def test_t15_valor_fora_da_faixa_e_rejeitado(campo, valor):
    mensagem = erros_de(com_base(**{campo: valor}))
    assert f"base_conhecimento.{campo}" in mensagem
    assert "fora da faixa" in mensagem


@pytest.mark.parametrize(
    "campo",
    ["trechos_por_resposta", "tamanho_trecho", "sobreposicao_trecho"],
)
def test_t15_inteiro_nao_aceita_decimal_nem_texto(campo):
    assert "número inteiro" in erros_de(com_base(**{campo: 2.5}))
    assert "número inteiro" in erros_de(com_base(**{campo: "dois"}))


@pytest.mark.parametrize(
    "campo", ["peso_palavras", "peso_sentido", "similaridade_minima"]
)
def test_t15_decimal_nao_aceita_texto_nem_booleano(campo):
    assert "deveria ser um número" in erros_de(com_base(**{campo: "alto"}))
    assert "deveria ser um número" in erros_de(com_base(**{campo: True}))


def test_t15_campo_desconhecido_e_erro_com_os_aceitos():
    mensagem = erros_de(com_base(tamanho_do_trecho=100))
    assert "base_conhecimento.tamanho_do_trecho" in mensagem
    assert "campo desconhecido" in mensagem
    assert "tamanho_trecho" in mensagem  # diz o nome certo


def test_t15_bloco_que_nao_e_um_bloco_e_erro():
    dados = config_base()
    dados["base_conhecimento"] = "ligada"
    assert "deveria ser um bloco de campos" in erros_de(dados)


# --- pesos: zero desliga uma busca, mas não as duas ---------------------------


def test_t15_um_peso_zero_desliga_aquela_busca_e_e_aceito():
    so_sentido = interpretar(com_base(peso_palavras=0), raiz=RAIZ_DO_PROJETO)
    so_palavras = interpretar(com_base(peso_sentido=0), raiz=RAIZ_DO_PROJETO)
    assert so_sentido.base_conhecimento.peso_palavras == 0
    assert so_palavras.base_conhecimento.peso_sentido == 0


def test_t15_os_dois_pesos_em_zero_e_rejeitado():
    mensagem = erros_de(com_base(peso_palavras=0, peso_sentido=0))
    assert "os dois pesos estão em zero" in mensagem


def test_t15_erros_do_bloco_vem_junto_com_os_outros_erros():
    """Todos os erros de uma vez, como no resto do validador."""
    dados = com_base(tamanho_trecho=1)
    dados["aparencia"]["cor_primaria"] = "azul"
    mensagem = erros_de(dados)
    assert "base_conhecimento.tamanho_trecho" in mensagem
    assert "aparencia.cor_primaria" in mensagem
