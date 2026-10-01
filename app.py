"""O que o Hugging Face Space executa. É só a cola: tudo de verdade está em `src/`.

    python app.py        # roda local em http://localhost:7860
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

# O import vem depois do sys.path de propósito: o Space roda este arquivo solto e
# precisa ensinar o Python onde está src/.
from assistente.config import ErroDeConfiguracao, carregar  # noqa: E402
from assistente.interface import montar, opcoes_de_lancamento  # noqa: E402


def construir():
    """Lê o config.yaml e monta a tela. Config inválida impede o app de subir."""
    try:
        config = carregar(RAIZ / "config.yaml")
    except ErroDeConfiguracao as erro:
        print(f"❌ O config.yaml precisa de correção.\n\n{erro}", file=sys.stderr)
        raise SystemExit(1) from erro
    return config, montar(config, RAIZ)


if __name__ == "__main__":
    configuracao, tela = construir()
    tela.launch(**opcoes_de_lancamento(configuracao))
