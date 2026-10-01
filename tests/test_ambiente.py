"""Testes da leitura e escrita do `.env` local."""

import stat

from assistente.conhecimento.ambiente import aplicar_env, escrever_env, ler_env


def test_ler_ignora_comentario_linha_em_branco_e_aspas(tmp_path):
    arquivo = tmp_path / ".env"
    arquivo.write_text(
        "# comentário\n\nA=1\nexport B=dois\nC=\"entre aspas\"\nD='simples'\nE=\n",
        encoding="utf-8",
    )
    assert ler_env(arquivo) == {"A": "1", "B": "dois", "C": "entre aspas",
                                "D": "simples", "E": ""}


def test_arquivo_ausente_e_dicionario_vazio(tmp_path):
    assert ler_env(tmp_path / "nao-existe") == {}


def test_valor_com_igual_no_meio_nao_se_perde(tmp_path):
    arquivo = tmp_path / ".env"
    arquivo.write_text("URL=https://x.co/?a=b=c\n", encoding="utf-8")
    assert ler_env(arquivo)["URL"] == "https://x.co/?a=b=c"


def test_aplicar_nao_sobrescreve_o_que_ja_esta_no_ambiente(tmp_path):
    arquivo = tmp_path / ".env"
    arquivo.write_text("VELHA=do-arquivo\nNOVA=do-arquivo\nVAZIA=\n", encoding="utf-8")
    ambiente = {"VELHA": "do-github"}
    aplicados = aplicar_env(arquivo, ambiente)
    assert ambiente == {"VELHA": "do-github", "NOVA": "do-arquivo"}
    assert aplicados == ["NOVA"]  # só nomes, nunca valores


def test_escrever_cria_o_arquivo_so_para_o_dono(tmp_path):
    arquivo = tmp_path / ".env"
    escrever_env(arquivo, {"A": "1"})
    assert ler_env(arquivo) == {"A": "1"}
    assert stat.S_IMODE(arquivo.stat().st_mode) == 0o600


def test_escrever_mantem_comentarios_e_o_que_nao_mudou(tmp_path):
    arquivo = tmp_path / ".env"
    arquivo.write_text("# minhas chaves\nA=velho\nB=fica\n", encoding="utf-8")
    escrever_env(arquivo, {"A": "novo", "C": "acrescentada"})
    texto = arquivo.read_text(encoding="utf-8")
    assert "# minhas chaves" in texto
    assert ler_env(arquivo) == {"A": "novo", "B": "fica", "C": "acrescentada"}
