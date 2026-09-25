#!/usr/bin/env python3
"""Confere o config.yaml e devolve erro se algo estiver errado.

É o portão: roda no CI antes de publicar. Se este comando falhar, nada vai para
o ar e o site antigo continua funcionando.

    python scripts/validar_config.py            # confere o config.yaml da raiz
    python scripts/validar_config.py outro.yaml

Código de saída 0 = pode publicar. 1 = corrija antes.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

# O import vem depois do sys.path de propósito: este script roda solto, fora do
# pacote, e precisa ensinar o Python onde está src/. O noqa silencia a regra
# E402 só nesta linha, não no arquivo inteiro.
from assistente.config import Config, ErroDeConfiguracao, carregar  # noqa: E402


def _resumo(config: Config) -> str:
    """Mostra o que vai valer, para conferir de olho antes de publicar."""
    linhas = [
        f"  assistente      {config.assistente.nome}",
        (
            f"  cores           {config.aparencia.cor_primaria}"
            f" / {config.aparencia.cor_secundaria or '(só a primária)'}"
            f"  ·  tema {config.aparencia.tema}"
        ),
        f"  logo            {config.assistente.logo or '(sem logo)'}",
        f"  perguntas       {len(config.perguntas_exemplo)} botão(ões) de exemplo",
        f"  resposta até    {config.limites.tamanho_maximo_resposta} tokens",
        f"  por sessão      {config.limites.mensagens_por_sessao} mensagens",
        "  provedores, na ordem de preferência:",
    ]
    for i, p in enumerate(config.provedores, start=1):
        linhas.append(f"      {i}. {p.nome:<12} {p.modelo}")
    return "\n".join(linhas)


def main(argumentos: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    caminho = Path(argumentos[0]) if argumentos else RAIZ / "config.yaml"

    try:
        config = carregar(caminho)
    except ErroDeConfiguracao as erro:
        print(f"❌ {caminho} precisa de correção.\n", file=sys.stderr)
        print(erro, file=sys.stderr)
        print(
            "\nNada será publicado. O site atual continua no ar.",
            file=sys.stderr,
        )
        return 1

    print(f"✅ {caminho} está válido.\n")
    print(_resumo(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
