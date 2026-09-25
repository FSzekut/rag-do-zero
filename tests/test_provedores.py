"""Testes da fila de provedores — verificações T8 a T12 da spec.

Nenhum teste aqui toca a internet nem precisa de chave: no lugar do cliente de
verdade entra um dublê, que responde ou falha conforme o teste mandar. É o que
permite o portão do CI rodar em menos de um segundo, sem segredo nenhum.
"""

from pathlib import Path

import pytest

from assistente.config import carregar
from assistente.provedores import (
    Resposta,
    disponiveis,
    instrucao_do_sistema,
    responder,
)

RAIZ = Path(__file__).resolve().parent.parent
CHAVE_FALSA = "sk-or-v1-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


@pytest.fixture
def config():
    return carregar(RAIZ / "config.yaml")


class ErroDeAPI(Exception):
    """Imita o erro dos SDKs, que trazem `status_code`."""

    def __init__(self, status_code: int, mensagem: str = "falhou") -> None:
        super().__init__(mensagem)
        self.status_code = status_code


class ClienteDeMentira:
    def __init__(self, resposta: str = "", erro: Exception | None = None) -> None:
        self.resposta = resposta
        self.erro = erro
        self.chamadas: list[str] = []

    def conversar(self, modelo, instrucao, mensagens, limite_de_tokens) -> str:
        self.chamadas.append(modelo)
        if self.erro:
            raise self.erro
        return self.resposta


def fabrica_de(clientes: dict[str, ClienteDeMentira]):
    """Devolve uma fábrica que entrega o dublê certo para cada provedor."""
    chamados: list[str] = []

    def fabrica(nome: str, chave: str):
        chamados.append(nome)
        return clientes[nome]

    fabrica.chamados = chamados
    return fabrica


PERGUNTA = [{"role": "user", "content": "O que é um data lake?"}]


# --- T8: só entra na fila quem tem chave --------------------------------------


def test_t8_provedor_sem_chave_fica_de_fora(config):
    fila = disponiveis(config.provedores, {"ANTHROPIC_API_KEY": "x"})
    assert [p.nome for p in fila] == ["anthropic"]


def test_t8_chave_vazia_ou_com_espaco_nao_vale(config):
    fila = disponiveis(
        config.provedores, {"OPENROUTER_API_KEY": "", "ANTHROPIC_API_KEY": "   "}
    )
    assert fila == []


def test_t8_a_ordem_do_config_manda(config):
    fila = disponiveis(
        config.provedores, {"OPENAI_API_KEY": "x", "OPENROUTER_API_KEY": "y"}
    )
    assert [p.nome for p in fila] == ["openrouter", "openai"]


def test_t8_provedor_sem_chave_nao_e_nem_construido(config):
    """Não basta não usar: nem cliente dele pode ser criado."""
    clientes = {"anthropic": ClienteDeMentira(resposta="oi")}
    fabrica = fabrica_de(clientes)
    responder(
        config, PERGUNTA, ambiente={"ANTHROPIC_API_KEY": "x"}, fabrica=fabrica
    )
    assert fabrica.chamados == ["anthropic"]


# --- T9: a troca automática ---------------------------------------------------


def test_t9_primeiro_falha_e_o_segundo_responde(config):
    clientes = {
        "openrouter": ClienteDeMentira(erro=ErroDeAPI(429, "modelo lotado")),
        "anthropic": ClienteDeMentira(resposta="Um data lake é..."),
    }
    resultado = responder(
        config,
        PERGUNTA,
        ambiente={"OPENROUTER_API_KEY": "a", "ANTHROPIC_API_KEY": "b"},
        fabrica=fabrica_de(clientes),
    )
    assert resultado.texto == "Um data lake é..."
    assert resultado.provedor == "anthropic"
    assert resultado.tentativas[0].ok is False
    assert "429" in resultado.tentativas[0].motivo


def test_t9_quem_respondeu_encerra_a_fila(config):
    """O terceiro não pode ser chamado se o primeiro já respondeu."""
    clientes = {
        "openrouter": ClienteDeMentira(resposta="resposta boa"),
        "anthropic": ClienteDeMentira(resposta="não deveria ser chamado"),
        "openai": ClienteDeMentira(resposta="nem este"),
    }
    fabrica = fabrica_de(clientes)
    resultado = responder(
        config,
        PERGUNTA,
        ambiente={
            "OPENROUTER_API_KEY": "a",
            "ANTHROPIC_API_KEY": "b",
            "OPENAI_API_KEY": "c",
        },
        fabrica=fabrica,
    )
    assert resultado.provedor == "openrouter"
    assert fabrica.chamados == ["openrouter"]


@pytest.mark.parametrize(
    "status,trecho",
    [
        (401, "chave inválida"),
        (402, "sem crédito"),
        (404, "modelo não encontrado"),
        (429, "lotado"),
        (503, "fora do ar"),
    ],
)
def test_t9_cada_tipo_de_falha_vira_frase_legivel(config, status, trecho):
    clientes = {
        "openrouter": ClienteDeMentira(erro=ErroDeAPI(status)),
        "anthropic": ClienteDeMentira(resposta="ok"),
    }
    resultado = responder(
        config,
        PERGUNTA,
        ambiente={"OPENROUTER_API_KEY": "a", "ANTHROPIC_API_KEY": "b"},
        fabrica=fabrica_de(clientes),
    )
    assert trecho in resultado.tentativas[0].motivo


def test_t9_resposta_vazia_conta_como_falha(config):
    clientes = {
        "openrouter": ClienteDeMentira(resposta="   "),
        "anthropic": ClienteDeMentira(resposta="resposta de verdade"),
    }
    resultado = responder(
        config,
        PERGUNTA,
        ambiente={"OPENROUTER_API_KEY": "a", "ANTHROPIC_API_KEY": "b"},
        fabrica=fabrica_de(clientes),
    )
    assert resultado.provedor == "anthropic"


def test_t9_um_provedor_so_e_suficiente(config):
    clientes = {"openai": ClienteDeMentira(resposta="respondi sozinho")}
    resultado = responder(
        config, PERGUNTA, ambiente={"OPENAI_API_KEY": "x"},
        fabrica=fabrica_de(clientes),
    )
    assert resultado.deu_certo
    assert resultado.provedor == "openai"


# --- T10: todos falharem vira relatório ---------------------------------------


def test_t10_relatorio_nomeia_cada_provedor_e_o_motivo(config):
    clientes = {
        "openrouter": ClienteDeMentira(erro=ErroDeAPI(429)),
        "anthropic": ClienteDeMentira(erro=ErroDeAPI(402)),
        "openai": ClienteDeMentira(erro=ErroDeAPI(500)),
    }
    resultado = responder(
        config,
        PERGUNTA,
        ambiente={
            "OPENROUTER_API_KEY": "a",
            "ANTHROPIC_API_KEY": "b",
            "OPENAI_API_KEY": "c",
        },
        fabrica=fabrica_de(clientes),
    )
    assert isinstance(resultado, Resposta)
    assert not resultado.deu_certo
    for provedor in ("openrouter", "anthropic", "openai"):
        assert provedor in resultado.texto
    assert "lotado" in resultado.texto
    assert "sem crédito" in resultado.texto
    assert len(resultado.tentativas) == 3


def test_t10_falha_de_conexao_tambem_e_explicada(config):
    class APIConnectionError(Exception):
        pass

    clientes = {"openrouter": ClienteDeMentira(erro=APIConnectionError("sem rede"))}
    resultado = responder(
        config, PERGUNTA, ambiente={"OPENROUTER_API_KEY": "a"},
        fabrica=fabrica_de(clientes),
    )
    assert "conectar" in resultado.texto


# --- T11: sem chave nenhuma o app não quebra ----------------------------------


def test_t11_sem_chave_devolve_explicacao_em_vez_de_excecao(config):
    resultado = responder(config, PERGUNTA, ambiente={}, fabrica=fabrica_de({}))
    assert isinstance(resultado, Resposta)
    assert not resultado.deu_certo
    assert resultado.tentativas == []


def test_t11_a_explicacao_diz_os_nomes_exatos_das_variaveis(config):
    """O erro mais comum é criar o segredo com o nome abreviado."""
    resultado = responder(config, PERGUNTA, ambiente={}, fabrica=fabrica_de({}))
    assert "OPENROUTER_API_KEY" in resultado.texto
    assert "ANTHROPIC_API_KEY" in resultado.texto
    assert "Settings" in resultado.texto


# --- T12: nenhuma mensagem pode vazar a chave ---------------------------------


def test_t12_a_chave_nao_aparece_quando_o_erro_a_repete(config):
    erro = ErroDeAPI(401, f"Invalid api key: {CHAVE_FALSA}")
    clientes = {"openrouter": ClienteDeMentira(erro=erro)}
    resultado = responder(
        config, PERGUNTA, ambiente={"OPENROUTER_API_KEY": CHAVE_FALSA},
        fabrica=fabrica_de(clientes),
    )
    assert CHAVE_FALSA not in resultado.texto
    assert CHAVE_FALSA not in resultado.tentativas[0].motivo


def test_t12_chave_de_outro_formato_tambem_e_escondida(config):
    vazada = "sk-ant-api03-ABCDEFGHIJKLMNOP1234567890"
    clientes = {
        "anthropic": ClienteDeMentira(erro=Exception(f"erro com {vazada} no texto"))
    }
    resultado = responder(
        config, PERGUNTA, ambiente={"ANTHROPIC_API_KEY": "outra-coisa"},
        fabrica=fabrica_de(clientes),
    )
    assert vazada not in resultado.texto
    assert "***" in resultado.texto


# --- a instrução enviada ao modelo --------------------------------------------


def test_instrucao_junta_papel_publico_e_proibicoes(config):
    texto = instrucao_do_sistema(config)
    assert "professor" in texto.lower()
    assert "pós-graduação" in texto
    assert "Não invente números" in texto
    assert "português" in texto.lower()
