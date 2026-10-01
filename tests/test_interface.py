"""Testes da tela — requisitos RF9, RF11, RF12, RF14 e RF18 da spec.

Nada aqui abre navegador nem chama provedor de IA: o que é lógica (CSS, cabeçalho,
histórico, limite) é testado como função pura, e a tela do Gradio só é montada,
nunca publicada.
"""

import dataclasses
from pathlib import Path

import pytest

from assistente.config import Config, carregar
from assistente.interface import (
    AVISO_DE_LIMITE,
    cabecalho_html,
    conversar,
    cor_do_texto_sobre,
    css_do_tema,
    js_do_tema,
    mensagens_para_o_modelo,
    montar,
    opcoes_de_lancamento,
)
from assistente.provedores import VARIAVEL_DE_CHAVE, Resposta

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def config() -> Config:
    return carregar(RAIZ / "config.yaml")


def com(config: Config, **blocos) -> Config:
    """Cópia da config com blocos trocados, ex.: com(c, aparencia=...)."""
    return dataclasses.replace(config, **blocos)


class RespondedorDeMentira:
    """Registra o que o modelo receberia e devolve um texto fixo."""

    def __init__(self, texto: str = "resposta de mentira") -> None:
        self.texto = texto
        self.recebidas: list[list[dict[str, str]]] = []

    def __call__(self, config, mensagens) -> Resposta:
        self.recebidas.append(list(mensagens))
        return Resposta(self.texto, "openrouter", "modelo", [])


# -- aparência (RF11) --------------------------------------------------------


def test_css_usa_as_cores_do_config(config):
    css = css_do_tema(config)
    assert config.aparencia.cor_primaria in css
    assert config.aparencia.cor_secundaria in css


def test_css_sem_secundaria_deixa_o_topo_transparente(config):
    aparencia = dataclasses.replace(config.aparencia, cor_secundaria="")
    css = css_do_tema(com(config, aparencia=aparencia))
    assert "background: transparent" in css


@pytest.mark.parametrize(
    ("fundo", "esperado"),
    [("#000000", "#ffffff"), ("#fff", "#111111"), ("#ffeb3b", "#111111"),
     ("#1f6feb", "#ffffff")],
)
def test_texto_legivel_sobre_qualquer_cor(fundo, esperado):
    assert cor_do_texto_sobre(fundo) == esperado


def test_tema_escuro_e_claro_forcam_a_classe_certa(config):
    escuro = dataclasses.replace(config.aparencia, tema="escuro")
    claro = dataclasses.replace(config.aparencia, tema="claro")
    assert "add('dark')" in js_do_tema(com(config, aparencia=escuro))
    assert "remove('dark')" in js_do_tema(com(config, aparencia=claro))


def test_cabecalho_mostra_nome_e_descricao(config):
    html = cabecalho_html(config, RAIZ)
    assert config.assistente.nome in html
    assert config.assistente.descricao in html
    assert "<img" not in html  # o config de exemplo não tem logo


def test_cabecalho_escapa_html_do_config(config):
    assistente = dataclasses.replace(
        config.assistente, nome="<script>alert(1)</script>", descricao="a & b"
    )
    html = cabecalho_html(com(config, assistente=assistente), RAIZ)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "a &amp; b" in html


def test_cabecalho_embute_a_logo_com_a_altura_pedida(config, tmp_path):
    (tmp_path / "logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    assistente = dataclasses.replace(
        config.assistente, logo="logo.svg", logo_altura_px=80
    )
    html = cabecalho_html(com(config, assistente=assistente), tmp_path)
    assert 'src="data:image/svg+xml;base64,' in html
    assert "height: 80px" in html


# -- histórico enviado ao modelo ---------------------------------------------


def test_boas_vindas_nao_vai_para_o_modelo():
    historico = [
        {"role": "assistant", "content": "Olá! Sobre o que quer falar?"},
        {"role": "user", "content": "O que é ETL?"},
    ]
    assert mensagens_para_o_modelo(historico) == [
        {"role": "user", "content": "O que é ETL?"}
    ]


def test_historico_fica_so_com_papel_e_texto():
    historico = [
        {"role": "user", "content": "oi", "metadata": {"x": 1}},
        {"role": "assistant", "content": [{"type": "text", "text": "olá"}]},
        {"role": "assistant", "content": "   "},
    ]
    assert mensagens_para_o_modelo(historico) == [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": "olá"},
    ]


# -- conversa, limite e chaves (RF9, RF14) -----------------------------------


def test_pergunta_vazia_nao_chama_o_modelo(config):
    responde = RespondedorDeMentira()
    assert conversar(config, [], "   ", responder_fn=responde) == []
    assert responde.recebidas == []


def test_conversa_acrescenta_pergunta_e_resposta(config):
    responde = RespondedorDeMentira("ETL extrai, transforma e carrega.")
    historico = conversar(config, [], "O que é ETL?", responder_fn=responde)
    assert historico == [
        {"role": "user", "content": "O que é ETL?"},
        {"role": "assistant", "content": "ETL extrai, transforma e carrega."},
    ]


def test_historico_vai_inteiro_para_o_modelo(config):
    responde = RespondedorDeMentira()
    h1 = conversar(config, [], "primeira", responder_fn=responde)
    conversar(config, h1, "segunda", responder_fn=responde)
    assert [m["content"] for m in responde.recebidas[1]] == [
        "primeira", "resposta de mentira", "segunda",
    ]


def test_passou_do_limite_avisa_e_para_de_responder(config):
    limites = dataclasses.replace(config.limites, mensagens_por_sessao=2)
    pequeno = com(config, limites=limites)
    responde = RespondedorDeMentira()

    historico: list = []
    for pergunta in ("um", "dois"):
        historico = conversar(pequeno, historico, pergunta, responder_fn=responde)
    assert len(responde.recebidas) == 2

    historico = conversar(pequeno, historico, "três", responder_fn=responde)
    assert len(responde.recebidas) == 2  # não chamou o modelo de novo
    assert historico[-1]["content"] == AVISO_DE_LIMITE.format(limite=2)


def test_boas_vindas_nao_conta_no_limite(config):
    limites = dataclasses.replace(config.limites, mensagens_por_sessao=1)
    pequeno = com(config, limites=limites)
    responde = RespondedorDeMentira()
    inicial = [{"role": "assistant", "content": "Olá!"}]
    historico = conversar(pequeno, inicial, "uma", responder_fn=responde)
    assert len(responde.recebidas) == 1
    assert historico[-1]["content"] == "resposta de mentira"


def test_sem_chave_nenhuma_o_chat_explica_o_que_falta(config, monkeypatch):
    """RF9: a tela abre e a primeira resposta diz como cadastrar a chave."""
    for variavel in VARIAVEL_DE_CHAVE.values():
        monkeypatch.delenv(variavel, raising=False)
    historico = conversar(config, [], "oi")
    texto = historico[-1]["content"]
    assert "Nenhuma chave de API está cadastrada" in texto
    assert "OPENROUTER_API_KEY" in texto


# -- a tela do Gradio --------------------------------------------------------


def test_tela_monta_com_um_botao_por_pergunta_de_exemplo(config):
    import gradio as gr

    tela = montar(config, RAIZ)
    botoes = [b.value for b in tela.blocks.values() if isinstance(b, gr.Button)]
    for pergunta in config.perguntas_exemplo:
        assert pergunta in botoes


def test_tela_mostra_a_boas_vindas_do_config(config):
    import gradio as gr

    tela = montar(config, RAIZ)
    chat = next(b for b in tela.blocks.values() if isinstance(b, gr.Chatbot))
    # O Gradio 6 guarda o conteúdo como lista de partes ({"type": "text", ...}),
    # por isso a comparação é por "contém" e não por igualdade.
    assert chat.value[0]["role"] == "assistant"
    assert config.comportamento.mensagem_boas_vindas in str(chat.value[0]["content"])


def test_opcoes_de_lancamento_levam_tema_css_e_js(config):
    opcoes = opcoes_de_lancamento(config)
    assert set(opcoes) == {"theme", "css", "js"}
    assert config.aparencia.cor_primaria in opcoes["css"]
