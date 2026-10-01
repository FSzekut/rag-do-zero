"""Ler e escrever o `.env` do computador local.

O `.env` guarda as chaves só para rodar no seu computador (o Space e o GitHub têm
os próprios Secrets). Ele nunca é versionado, e a varredura de segredos o ignora de
propósito: é o lugar combinado para chave.

Pequeno de propósito: o formato é `NOME=valor`, uma por linha. Nada de biblioteca
nova para isso.
"""

from __future__ import annotations

import os
from pathlib import Path


def _separar(linha: str) -> tuple[str, str] | None:
    """`NOME=valor` -> ("NOME", "valor"); comentário e linha em branco -> None."""
    limpa = linha.strip()
    if not limpa or limpa.startswith("#") or "=" not in limpa:
        return None
    nome, _, valor = limpa.partition("=")
    nome = nome.removeprefix("export ").strip()
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        valor = valor[1:-1]
    return nome, valor


def ler_env(caminho: Path) -> dict[str, str]:
    """Lê o arquivo. Arquivo ausente = dicionário vazio."""
    if not caminho.is_file():
        return {}
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    pares = (_separar(linha) for linha in linhas)
    return dict(p for p in pares if p)


def aplicar_env(caminho: Path, ambiente: dict[str, str] | None = None) -> list[str]:
    """Põe o conteúdo do `.env` no ambiente, **sem** sobrescrever o que já existe.

    Assim, no GitHub Actions, onde as variáveis vêm dos Secrets, um `.env` esquecido
    nunca vence. Devolve os nomes que foram aplicados (nunca os valores).
    """
    destino = os.environ if ambiente is None else ambiente
    aplicados = []
    for nome, valor in ler_env(caminho).items():
        if valor and not destino.get(nome):
            destino[nome] = valor
            aplicados.append(nome)
    return aplicados


def escrever_env(caminho: Path, novos: dict[str, str]) -> None:
    """Grava `novos` no arquivo, mantendo comentários e as outras variáveis.

    O arquivo fica legível só pelo dono (chmod 600).
    """
    linhas = (
        caminho.read_text(encoding="utf-8").splitlines() if caminho.is_file() else []
    )
    pendentes = dict(novos)
    saida = []
    for linha in linhas:
        par = _separar(linha)
        if par and par[0] in pendentes:
            saida.append(f"{par[0]}={pendentes.pop(par[0])}")
        else:
            saida.append(linha)
    saida.extend(f"{nome}={valor}" for nome, valor in pendentes.items())
    caminho.write_text("\n".join(saida) + "\n", encoding="utf-8")
    caminho.chmod(0o600)
