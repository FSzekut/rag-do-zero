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

# -- Exigência do ZeroGPU ------------------------------------------------------
# No plano grátis do Hugging Face, Space com SDK Gradio só roda em ZeroGPU: o
# CPU basic exige assinatura PRO. E o ZeroGPU recusa subir um app sem nenhuma
# função marcada com @spaces.GPU ("No @spaces.GPU function detected during
# startup"). Este app só chama APIs de IA e não usa GPU; a função abaixo existe
# apenas para cumprir a exigência e NUNCA é chamada, então não gasta cota de GPU.
# Se o Space for um dia para CPU basic (PRO), este bloco inteiro pode ser apagado.
try:
    import spaces
except ImportError:  # no computador e no CI o pacote não existe: sem efeito
    spaces = None

if spaces is not None:

    @spaces.GPU
    def _cumprir_exigencia_do_zerogpu() -> None:
        """Nunca é chamada."""


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
