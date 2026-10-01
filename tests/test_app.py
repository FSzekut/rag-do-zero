"""Teste do app.py — a cola entre o config.yaml e a tela, e a exigência do ZeroGPU.

O Space do plano grátis roda em ZeroGPU, que só sobe se existir ao menos uma
função com @spaces.GPU. No computador e no CI o pacote `spaces` não existe, e o
app precisa funcionar do mesmo jeito.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def carregar_app():
    """Importa o app.py solto, como o Space faz, e devolve o módulo."""
    especificacao = importlib.util.spec_from_file_location(
        "app_sob_teste", RAIZ / "app.py"
    )
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def sem_spaces(monkeypatch):
    monkeypatch.setitem(sys.modules, "spaces", None)  # None faz o import falhar


def test_app_sobe_sem_o_pacote_spaces(sem_spaces):
    app = carregar_app()
    assert app.spaces is None
    _config, tela = app.construir()
    assert tela is not None


def test_app_registra_uma_funcao_gpu_quando_o_zerogpu_existe(monkeypatch):
    registradas = []
    falso = types.ModuleType("spaces")
    falso.GPU = lambda funcao: registradas.append(funcao) or funcao
    monkeypatch.setitem(sys.modules, "spaces", falso)

    carregar_app()
    assert len(registradas) == 1


def test_config_invalido_impede_o_app_de_subir(sem_spaces, tmp_path, monkeypatch):
    app = carregar_app()
    ruim = tmp_path / "config.yaml"
    ruim.write_text("assistente: {}\n", encoding="utf-8")
    monkeypatch.setattr(app, "RAIZ", tmp_path)
    with pytest.raises(SystemExit) as saida:
        app.construir()
    assert saida.value.code == 1
