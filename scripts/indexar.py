#!/usr/bin/env python3
"""Reconstrói a coleção `teste` do banco a partir da pasta `documentos/`.

    python scripts/indexar.py              # apaga e reconstrói a coleção 'teste'
    python scripts/indexar.py --promover   # teste vira 'producao' (o que está no ar)

Precisa de `SUPABASE_URL` e `SUPABASE_SECRET_KEY`, do `.env` (no computador) ou dos
Secrets (no GitHub Actions). A coleção `producao` só é tocada com `--promover`, e
mesmo assim só se a coleção `teste` for a do commit atual.

Código de saída 0 = deu certo. 1 = falhou, com o motivo na tela.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

# Os imports vêm depois do sys.path de propósito (mesmo motivo do app.py).
from assistente.config import ErroDeConfiguracao, carregar  # noqa: E402
from assistente.conhecimento.ambiente import aplicar_env  # noqa: E402
from assistente.conhecimento.banco import Banco, ErroDoBanco  # noqa: E402
from assistente.conhecimento.embeddings import (  # noqa: E402
    EmbeddadorFastembed,
    ErroDeEmbedding,
)
from assistente.conhecimento.indexacao import ErroDeIndexacao, indexar  # noqa: E402


def descobrir_versao() -> str:
    """O hash do commit: do GitHub Actions, ou do git local, ou 'local'."""
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        saida = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=RAIZ, capture_output=True, text=True, check=True,
        )
        return saida.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "local"


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--promover", action="store_true",
                        help="promove a coleção teste para producao")
    args = parser.parse_args(argumentos)

    aplicar_env(RAIZ / ".env")
    obrigatorias = ("SUPABASE_URL", "SUPABASE_SECRET_KEY")
    faltam = [v for v in obrigatorias if not os.environ.get(v)]
    if faltam:
        print(f"❌ Faltam no .env ou no ambiente: {', '.join(faltam)}", file=sys.stderr)
        return 1

    try:
        config = carregar(RAIZ / "config.yaml")
    except ErroDeConfiguracao as erro:
        print(f"❌ {erro}", file=sys.stderr)
        return 1
    if config.base_conhecimento is None:
        print("❌ O config.yaml não tem o bloco base_conhecimento.", file=sys.stderr)
        return 1

    versao = descobrir_versao()
    banco = Banco(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    try:
        if args.promover:
            n = banco.promover(versao)
            print(f"✅ {n} trechos da versão {versao[:7]} agora estão em producao.")
            return 0
        resumo = indexar(
            RAIZ / "documentos", config.base_conhecimento, banco,
            EmbeddadorFastembed(), versao=versao, registrar=print,
        )
    except (ErroDeIndexacao, ErroDoBanco, ErroDeEmbedding) as erro:
        print(f"❌ {erro}", file=sys.stderr)
        return 1
    finally:
        banco.fechar()

    por_fonte = ", ".join(f"{n} de {f}" for f, n in resumo.por_fonte.items())
    print(f"✅ coleção teste reconstruída: {resumo.trechos} trechos ({por_fonte}), "
          f"versão {resumo.versao[:7]}, em {resumo.segundos:.0f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
