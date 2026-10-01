#!/usr/bin/env python3
"""Prova o que cada chave do Supabase pode e não pode fazer.

    python scripts/verificar_banco.py

Lê as chaves do `.env` (ou do ambiente) e **tenta** as coisas proibidas com a chave
publicável: ler a tabela, gravar, apagar, ver a coleção de teste, promover o índice.
Tudo isso tem que ser recusado. Depois confere que o que o app precisa funciona.

Código de saída 0 = o banco está como a spec manda. 1 = tem permissão errada.
Roda de novo sempre que o supabase/esquema.sql mudar.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

# O import vem depois do sys.path de propósito (mesmo motivo do app.py).
from assistente.conhecimento.ambiente import aplicar_env  # noqa: E402
from assistente.conhecimento.verificacao import verificar  # noqa: E402

VARIAVEIS = ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY")


def main() -> int:
    aplicar_env(RAIZ / ".env")
    faltam = [v for v in VARIAVEIS if not os.environ.get(v)]
    if faltam:
        print(f"❌ Faltam no .env ou no ambiente: {', '.join(faltam)}", file=sys.stderr)
        print("   Rode: .venv/bin/python scripts/criar_env.py", file=sys.stderr)
        return 1

    resultados = verificar(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_PUBLISHABLE_KEY"],
        os.environ["SUPABASE_SECRET_KEY"],
    )
    quem_atual = ""
    for r in resultados:
        if r.quem != quem_atual:
            quem_atual = r.quem
            print(f"\nChave {r.quem}:")
        marca = "✅" if r.ok else "❌"
        status = r.status if r.status is not None else "—"
        print(f"  {marca} {r.o_que:<62} deve ser {r.esperado:<9} (HTTP {status})")
        if r.dica:
            print(f"       → {r.dica}")

    erros = [r for r in resultados if not r.ok]
    if erros:
        print(f"\n❌ {len(erros)} verificação(ões) fora do esperado.", file=sys.stderr)
        return 1
    print("\n✅ O banco está como a spec manda: cada chave faz só o que deve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
