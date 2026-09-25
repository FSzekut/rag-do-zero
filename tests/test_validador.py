"""Teste do portão — verificação T13 da spec.

Aqui o comando é chamado como o CI chama: um processo separado, e o que importa
é o código de saída. 0 libera a publicação, 1 barra.
"""

import subprocess
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
VALIDADOR = RAIZ / "scripts" / "validar_config.py"


def rodar(*argumentos: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDADOR), *argumentos],
        capture_output=True,
        text=True,
        check=False,
    )


def escrever(pasta: Path, mudanca) -> Path:
    dados = yaml.safe_load(
        (RAIZ / "tests" / "exemplos" / "config_valido.yaml").read_text(encoding="utf-8")
    )
    mudanca(dados)
    destino = pasta / "config.yaml"
    destino.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return destino


def test_t13_config_valido_sai_com_zero():
    resultado = rodar(str(RAIZ / "config.yaml"))
    assert resultado.returncode == 0
    assert "válido" in resultado.stdout


def test_t13_config_quebrado_sai_com_um(tmp_path):
    caminho = escrever(tmp_path, lambda d: d["aparencia"].update(cor_primaria="azul"))
    resultado = rodar(str(caminho))
    assert resultado.returncode == 1
    assert "cor_primaria" in resultado.stderr


def test_t13_arquivo_inexistente_sai_com_um(tmp_path):
    resultado = rodar(str(tmp_path / "nao-existe.yaml"))
    assert resultado.returncode == 1


def test_t13_sem_argumento_usa_o_config_da_raiz():
    resultado = rodar()
    assert resultado.returncode == 0


def test_t13_o_resumo_mostra_os_provedores_na_ordem():
    """Conferir de olho antes de publicar é metade do valor do portão."""
    resultado = rodar(str(RAIZ / "config.yaml"))
    saida = resultado.stdout
    assert "1. openrouter" in saida
    assert saida.index("openrouter") < saida.index("anthropic")


def test_t13_erro_vai_para_stderr_e_nao_para_stdout(tmp_path):
    caminho = escrever(tmp_path, lambda d: d["assistente"].pop("nome"))
    resultado = rodar(str(caminho))
    assert "assistente.nome" in resultado.stderr
    assert "assistente.nome" not in resultado.stdout
