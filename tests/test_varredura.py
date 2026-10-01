"""Teste da varredura de segredos — verificação T14 da spec.

Como no teste do validador, o comando roda como o CI roda: processo separado, e o
que vale é o código de saída. As chaves "plantadas" são montadas em tempo de
execução, para este arquivo não ter nenhuma chave escrita nele.
"""

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
VARREDURA = RAIZ / "scripts" / "varredura_segredos.py"

MIOLO = "A1b2C3d4E5f6G7h8I9j0"  # 20 caracteres, o mínimo para parecer chave

CHAVES_PLANTADAS = {
    "anthropic": "sk-ant-api03-" + MIOLO,
    "openrouter": "sk-or-v1-" + MIOLO,
    "formato sk-": "sk-proj-" + MIOLO,
    "huggingface": "hf_" + MIOLO,
}


def rodar(pasta: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VARREDURA), str(pasta)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("chave", CHAVES_PLANTADAS.values(), ids=CHAVES_PLANTADAS)
def test_t14_chave_plantada_barra_a_publicacao(tmp_path, chave):
    (tmp_path / "config.py").write_text(f'CHAVE = "{chave}"\n', encoding="utf-8")
    resultado = rodar(tmp_path)
    assert resultado.returncode == 1
    assert "config.py:1" in resultado.stderr


def test_relatorio_nunca_mostra_a_chave_inteira(tmp_path):
    chave = CHAVES_PLANTADAS["anthropic"]
    (tmp_path / "x.txt").write_text(chave, encoding="utf-8")
    resultado = rodar(tmp_path)
    assert chave not in resultado.stderr + resultado.stdout
    assert chave[:8] in resultado.stderr


def test_pasta_limpa_sai_com_zero(tmp_path):
    (tmp_path / "leia.md").write_text("Use sk-ant- e hf_ como prefixos.", "utf-8")
    resultado = rodar(tmp_path)
    assert resultado.returncode == 0


def test_prefixo_curto_no_meio_de_uma_frase_nao_e_chave(tmp_path):
    (tmp_path / "spec.md").write_text("Procura `sk-ant-`, `sk-or-` e `hf_`.", "utf-8")
    assert rodar(tmp_path).returncode == 0


def test_marcador_libera_chave_falsa_de_teste(tmp_path):
    linha = f'CHAVE = "{CHAVES_PLANTADAS["openrouter"]}"  # segredo-falso\n'
    (tmp_path / "teste.py").write_text(linha, encoding="utf-8")
    assert rodar(tmp_path).returncode == 0


def test_marcador_vale_so_para_a_propria_linha(tmp_path):
    texto = (
        "# segredo-falso\n"
        f'CHAVE = "{CHAVES_PLANTADAS["huggingface"]}"\n'
    )
    (tmp_path / "teste.py").write_text(texto, encoding="utf-8")
    assert rodar(tmp_path).returncode == 1


def test_env_local_e_pastas_de_ambiente_nao_entram(tmp_path):
    chave = CHAVES_PLANTADAS["openrouter"]
    (tmp_path / ".env").write_text(f"OPENROUTER_API_KEY={chave}\n", encoding="utf-8")
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "x.py").write_text(chave, encoding="utf-8")
    assert rodar(tmp_path).returncode == 0


def test_arquivo_binario_nao_derruba_a_varredura(tmp_path):
    (tmp_path / "figura.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00\x80")
    assert rodar(tmp_path).returncode == 0


def test_o_repositorio_de_verdade_esta_limpo():
    """O que o CI vai rodar: se isto falha, tem chave no repositório."""
    resultado = rodar(RAIZ)
    assert resultado.returncode == 0, resultado.stderr
