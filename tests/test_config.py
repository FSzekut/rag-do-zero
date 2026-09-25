"""Testes do leitor de configuração — verificações T2 a T7 da spec.

Rodam sem chave de API e sem internet: é só leitura de arquivo e comparação.

O padrão usado aqui: parte-se sempre da configuração válida em
`tests/exemplos/config_valido.yaml`, muda-se **uma** coisa, e confere-se que o
erro apareceu. Assim cada teste falha por um motivo só.
"""

from pathlib import Path

import pytest
import yaml

from assistente.config import Config, ErroDeConfiguracao, carregar, interpretar

EXEMPLOS = Path(__file__).parent / "exemplos"
RAIZ_DO_PROJETO = Path(__file__).parent.parent


def config_base() -> dict:
    """A configuração válida, lida do disco a cada teste."""
    return yaml.safe_load((EXEMPLOS / "config_valido.yaml").read_text(encoding="utf-8"))


def erros_de(dados: dict, raiz: Path | None = None) -> list[str]:
    """Roda a validação e devolve a lista de erros, exigindo que haja algum."""
    with pytest.raises(ErroDeConfiguracao) as capturado:
        interpretar(dados, raiz=raiz or RAIZ_DO_PROJETO)
    return capturado.value.erros


def texto_dos_erros(dados: dict, raiz: Path | None = None) -> str:
    return " | ".join(erros_de(dados, raiz))


# --- T2: a configuração válida carrega ---------------------------------------


def test_t2_exemplo_valido_carrega():
    config = interpretar(config_base(), raiz=RAIZ_DO_PROJETO)
    assert isinstance(config, Config)
    assert config.assistente.nome == "Professor de Engenharia de Dados"
    assert config.aparencia.tema == "escuro"
    assert len(config.perguntas_exemplo) == 3
    assert [p.nome for p in config.provedores] == ["openrouter", "anthropic", "openai"]


def test_t2_config_do_projeto_carrega():
    """O config.yaml de verdade, na raiz, precisa ser válido."""
    config = carregar(RAIZ_DO_PROJETO / "config.yaml")
    assert config.provedores


def test_t2_padroes_sao_aplicados_quando_o_campo_falta():
    dados = config_base()
    del dados["limites"]
    del dados["perguntas_exemplo"]
    del dados["aparencia"]["tema"]
    config = interpretar(dados, raiz=RAIZ_DO_PROJETO)
    assert config.limites.tamanho_maximo_resposta == 800
    assert config.limites.mensagens_por_sessao == 20
    assert config.perguntas_exemplo == []
    assert config.aparencia.tema == "claro"


# --- T3: campo obrigatório ausente é recusado ---------------------------------


@pytest.mark.parametrize(
    "bloco,campo",
    [
        ("assistente", "nome"),
        ("assistente", "descricao"),
        ("aparencia", "cor_primaria"),
        ("comportamento", "papel"),
    ],
)
def test_t3_campo_obrigatorio_ausente(bloco, campo):
    dados = config_base()
    del dados[bloco][campo]
    assert f"{bloco}.{campo}" in texto_dos_erros(dados)


def test_t3_campo_obrigatorio_vazio_tambem_e_erro():
    dados = config_base()
    dados["assistente"]["nome"] = "   "
    assert "assistente.nome" in texto_dos_erros(dados)


def test_t3_bloco_inteiro_ausente():
    dados = config_base()
    del dados["comportamento"]
    assert "comportamento" in texto_dos_erros(dados)


def test_t3_lista_completa_de_erros_de_uma_vez():
    """Três erros no arquivo devem virar três linhas, não uma."""
    dados = config_base()
    del dados["assistente"]["nome"]
    dados["aparencia"]["cor_primaria"] = "azul"
    dados["limites"]["mensagens_por_sessao"] = 999
    assert len(erros_de(dados)) == 3


# --- T4: valor fora do domínio é recusado -------------------------------------


@pytest.mark.parametrize("cor", ["azul", "1f6feb", "#12345", "#gggggg", "#"])
def test_t4_cor_invalida(cor):
    dados = config_base()
    dados["aparencia"]["cor_primaria"] = cor
    assert "aparencia.cor_primaria" in texto_dos_erros(dados)


@pytest.mark.parametrize("cor", ["#fff", "#FFF", "#1f6feb", "#1F6FEB"])
def test_t4_cor_valida_passa(cor):
    dados = config_base()
    dados["aparencia"]["cor_primaria"] = cor
    assert interpretar(dados, raiz=RAIZ_DO_PROJETO).aparencia.cor_primaria == cor


@pytest.mark.parametrize("altura", [15, 201, 0, -10])
def test_t4_altura_da_logo_fora_da_faixa(altura):
    dados = config_base()
    dados["assistente"]["logo_altura_px"] = altura
    assert "assistente.logo_altura_px" in texto_dos_erros(dados)


def test_t4_altura_da_logo_como_texto():
    dados = config_base()
    dados["assistente"]["logo_altura_px"] = "64"
    assert "inteiro" in texto_dos_erros(dados)


@pytest.mark.parametrize("tema", ["dark", "Claro", "meio-termo"])
def test_t4_tema_invalido(tema):
    dados = config_base()
    dados["aparencia"]["tema"] = tema
    assert "aparencia.tema" in texto_dos_erros(dados)


@pytest.mark.parametrize(
    "campo,valor", [("tamanho_maximo_resposta", 99), ("mensagens_por_sessao", 201)]
)
def test_t4_limites_fora_da_faixa(campo, valor):
    dados = config_base()
    dados["limites"][campo] = valor
    assert f"limites.{campo}" in texto_dos_erros(dados)


def test_t4_perguntas_de_exemplo_demais():
    dados = config_base()
    dados["perguntas_exemplo"] = [f"Pergunta {i}?" for i in range(7)]
    assert "perguntas_exemplo" in texto_dos_erros(dados)


# --- T5: campo desconhecido é recusado ----------------------------------------


def test_t5_campo_com_acento_e_recusado():
    """O erro clássico: acentuar o nome do campo e a cor "não funcionar"."""
    dados = config_base()
    dados["aparencia"]["cor_primária"] = "#ff0000"
    erros = texto_dos_erros(dados)
    assert "cor_primária" in erros
    assert "desconhecido" in erros


def test_t5_bloco_inventado_na_raiz():
    dados = config_base()
    dados["aparencias"] = {"cor": "#fff"}
    assert "aparencias" in texto_dos_erros(dados)


def test_t5_erro_lista_os_campos_aceitos():
    """A mensagem tem que ensinar o nome certo, não só dizer que está errado."""
    dados = config_base()
    dados["assistente"]["titulo"] = "x"
    assert "nome" in texto_dos_erros(dados)


# --- T6: logo que não existe é recusada ---------------------------------------


def test_t6_logo_inexistente():
    dados = config_base()
    dados["assistente"]["logo"] = "assets/logo-que-nao-existe.png"
    assert "assistente.logo" in texto_dos_erros(dados)


def test_t6_logo_com_extensao_nao_aceita():
    dados = config_base()
    dados["assistente"]["logo"] = "assets/logo.bmp"
    assert "extensão" in texto_dos_erros(dados)


def test_t6_logo_existente_passa(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.png").write_bytes(b"png de mentira")
    dados = config_base()
    dados["assistente"]["logo"] = "assets/logo.png"
    assert interpretar(dados, raiz=tmp_path).assistente.logo == "assets/logo.png"


def test_t6_logo_vazia_e_valida():
    dados = config_base()
    dados["assistente"]["logo"] = ""
    assert interpretar(dados, raiz=RAIZ_DO_PROJETO).assistente.logo == ""


# --- T7: a lista de provedores é validada -------------------------------------


def test_t7_lista_vazia():
    dados = config_base()
    dados["provedores"] = []
    assert "provedores" in texto_dos_erros(dados)


def test_t7_campo_provedores_ausente():
    dados = config_base()
    del dados["provedores"]
    assert "provedores" in texto_dos_erros(dados)


def test_t7_provedor_desconhecido():
    dados = config_base()
    dados["provedores"] = [{"nome": "gemini", "modelo": "gemini-pro"}]
    erros = texto_dos_erros(dados)
    assert "gemini" in erros
    assert "openrouter" in erros  # a mensagem ensina os aceitos


def test_t7_provedor_repetido():
    dados = config_base()
    dados["provedores"] = [
        {"nome": "openai", "modelo": "gpt-6-sol"},
        {"nome": "openai", "modelo": "gpt-5.5"},
    ]
    assert "mais de uma vez" in texto_dos_erros(dados)


def test_t7_modelo_vazio():
    dados = config_base()
    dados["provedores"] = [{"nome": "openrouter", "modelo": ""}]
    assert "modelo" in texto_dos_erros(dados)


def test_t7_um_provedor_so_e_valido():
    dados = config_base()
    dados["provedores"] = [{"nome": "anthropic", "modelo": "claude-opus-5"}]
    config = interpretar(dados, raiz=RAIZ_DO_PROJETO)
    assert len(config.provedores) == 1


def test_t7_a_ordem_do_arquivo_e_preservada():
    """A ordem é a preferência — inverter no arquivo tem que inverter na fila."""
    dados = config_base()
    dados["provedores"] = [
        {"nome": "anthropic", "modelo": "claude-opus-5"},
        {"nome": "openrouter", "modelo": "google/gemma-4-31b-it:free"},
    ]
    config = interpretar(dados, raiz=RAIZ_DO_PROJETO)
    assert [p.nome for p in config.provedores] == ["anthropic", "openrouter"]


# --- arquivo em si ------------------------------------------------------------


def test_arquivo_inexistente_da_erro_claro():
    with pytest.raises(ErroDeConfiguracao) as capturado:
        carregar("nao-existe.yaml")
    assert "não foi encontrado" in str(capturado.value)


def test_yaml_mal_formado_da_erro_claro(tmp_path):
    ruim = tmp_path / "config.yaml"
    ruim.write_text("assistente:\n  nome: 'sem fechar\n", encoding="utf-8")
    with pytest.raises(ErroDeConfiguracao) as capturado:
        carregar(ruim)
    assert "mal formado" in str(capturado.value)
