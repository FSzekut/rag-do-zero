"""Conferir a pasta `documentos/` (RF19) — a verificação T17.

Roda sem rede e sem chave. Devolve a **lista** de problemas, não só o primeiro,
pelo mesmo motivo do validador do config: corrigir, publicar e descobrir o próximo
é desperdício.
"""

from __future__ import annotations

from pathlib import Path

from .trechos import CERCA, TITULO

PALAVRAS_MINIMAS = 20  # menos que isso não é "conteúdo": é só um título


def _tem_titulo_e_conteudo(texto: str) -> tuple[bool, int]:
    """Tem um `#` de nível 1 (fora de bloco de código)? Quantas palavras de corpo?"""
    tem_titulo, dentro_de_codigo, palavras = False, False, 0
    for linha in texto.splitlines():
        if CERCA.match(linha):
            dentro_de_codigo = not dentro_de_codigo
            palavras += len(linha.split())
            continue
        titulo = None if dentro_de_codigo else TITULO.match(linha)
        if titulo:
            tem_titulo = tem_titulo or len(titulo.group(1)) == 1
            continue
        palavras += len(linha.split())
    return tem_titulo, palavras


def verificar_pasta(pasta: Path) -> list[str]:
    """Lista o que está errado na pasta de documentos. Lista vazia = tudo certo."""
    if not pasta.is_dir():
        return [f'a pasta "{pasta}" não existe']

    itens = sorted(pasta.iterdir())
    if not itens:
        return [f'a pasta "{pasta.name}" está vazia: a base não teria o que consultar']

    problemas: list[str] = []
    for item in itens:
        if item.is_dir():
            problemas.append(
                f'"{item.name}" é uma subpasta: só arquivos .md são aceitos'
            )
            continue
        if item.suffix != ".md":
            problemas.append(
                f'"{item.name}" não é .md — PDF e Word ficam fora do repositório; '
                "converta para Markdown e revise antes de colocar aqui"
            )
            continue
        try:
            texto = item.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problemas.append(f'"{item.name}" não é um texto em UTF-8')
            continue
        tem_titulo, palavras = _tem_titulo_e_conteudo(texto)
        if not tem_titulo:
            problemas.append(
                f'"{item.name}" não tem título: falta uma linha começando com "# "'
            )
        if palavras < PALAVRAS_MINIMAS:
            problemas.append(
                f'"{item.name}" quase não tem conteúdo '
                f"({palavras} palavras fora os títulos)"
            )
    return problemas
