#!/usr/bin/env python3
"""Cria (ou atualiza) o `.env` local pedindo as chaves, sem mostrar o que você digita.

    ! .venv/bin/python scripts/criar_env.py

Por que um script e não colar a chave no chat ou no terminal: o que se digita no
terminal fica no histórico do shell, e o que vai ao chat vai a terceiros. Aqui a
chave entra por uma pergunta escondida e vai direto para o arquivo, que só o seu
usuário consegue ler (chmod 600) e que o git nunca versiona.

Apertar Enter sem digitar nada mantém o valor que já estava no arquivo.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

# O import vem depois do sys.path de propósito (mesmo motivo do app.py).
from assistente.conhecimento.ambiente import escrever_env, ler_env  # noqa: E402

# (nome, secreto?, para que serve)
CAMPOS = (
    ("SUPABASE_URL", False, "a URL do projeto (termina em .supabase.co)"),
    ("SUPABASE_PUBLISHABLE_KEY", True, "a chave PUBLICÁVEL (a do Space, só lê)"),
    ("SUPABASE_SECRET_KEY", True, "a chave SECRETA (a do GitHub, grava)"),
    ("OPENROUTER_API_KEY", True, "opcional: a chave do modelo, para o chat local"),
)


def main() -> int:
    arquivo = RAIZ / ".env"
    atuais = ler_env(arquivo)
    novos: dict[str, str] = {}
    print(f"Vou gravar em {arquivo.name} (fica só no seu computador).")
    print("Enter sem digitar nada mantém o valor atual.\n")
    for nome, secreto, para_que in CAMPOS:
        situacao = "já definida" if atuais.get(nome) else "ainda vazia"
        pergunta = f"{nome} — {para_que} [{situacao}]: "
        valor = (getpass.getpass(pergunta) if secreto else input(pergunta)).strip()
        if valor:
            novos[nome] = valor
    if not novos:
        print("\nNada novo digitado: o arquivo ficou como estava.")
        return 0
    escrever_env(arquivo, novos)
    print(f"\nGravado: {', '.join(novos)}. (Os valores não foram mostrados.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
