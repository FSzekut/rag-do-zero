#!/usr/bin/env python3
"""Varre os arquivos atrás de chaves de API esquecidas e devolve erro se achar.

É a última linha do portão (RF17): roda no CI antes de publicar. Se este comando
falhar, nada vai para o ar. O repositório é público, então uma chave commitada
por engano é uma chave vazada.

    python scripts/varredura_segredos.py          # varre o repositório
    python scripts/varredura_segredos.py pasta/   # varre outra pasta

Código de saída 0 = limpo. 1 = achou algo.

Dois cuidados de projeto:

- **O relatório nunca imprime a chave inteira.** O log do CI também é público;
  mostrar só o começo basta para localizar o problema.
- **Chave falsa de teste precisa avisar.** Uma linha com `segredo-falso` (num
  comentário, por exemplo) é ignorada. É explícito de propósito: ignorar a
  pasta `tests/` inteira deixaria passar uma chave verdadeira colada ali.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# (nome para o relatório, padrão). Os tamanhos mínimos evitam falso alarme em
# texto comum: a spec cita "sk-ant-" no meio de uma frase, e isso não é chave.
PADROES = (
    ("chave da Anthropic (sk-ant-)", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("chave do OpenRouter (sk-or-)", re.compile(r"sk-or-[A-Za-z0-9_\-]{20,}")),
    ("chave no formato sk-", re.compile(r"sk-[A-Za-z0-9_\-]{20,}")),
    ("token do Hugging Face (hf_)", re.compile(r"hf_[A-Za-z0-9]{20,}")),
)

MARCADOR_DE_CHAVE_FALSA = "segredo-falso"

# O .env é o lugar combinado para chave no computador local: nunca é versionado,
# então não faz sentido o portão reclamar dele.
PASTAS_IGNORADAS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", "material-curso",
}
ARQUIVOS_IGNORADOS = {".env"}


@dataclass(frozen=True)
class Achado:
    arquivo: Path
    linha: int
    tipo: str
    inicio: str  # só o começo do valor, nunca a chave inteira


def _esconder(valor: str) -> str:
    return valor[:8] + "…"


def varrer_texto(texto: str) -> list[tuple[int, str, str]]:
    """Devolve (linha, tipo, inicio) para cada chave achada no texto."""
    achados: list[tuple[int, str, str]] = []
    for numero, linha in enumerate(texto.splitlines(), start=1):
        if MARCADOR_DE_CHAVE_FALSA in linha:
            continue
        for tipo, padrao in PADROES:
            casou = padrao.search(linha)
            if casou:
                achados.append((numero, tipo, _esconder(casou.group())))
                break  # uma linha, um achado: o mais específico vem primeiro
    return achados


def arquivos_para_varrer(raiz: Path):
    for caminho in sorted(raiz.rglob("*")):
        partes = caminho.relative_to(raiz).parts
        if any(p in PASTAS_IGNORADAS for p in partes[:-1]):
            continue
        if caminho.is_file() and caminho.name not in ARQUIVOS_IGNORADOS:
            yield caminho


def varrer(raiz: Path) -> list[Achado]:
    achados: list[Achado] = []
    for caminho in arquivos_para_varrer(raiz):
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binário (PDF, imagem): não é lugar de chave em texto
        for linha, tipo, inicio in varrer_texto(texto):
            achados.append(Achado(caminho.relative_to(raiz), linha, tipo, inicio))
    return achados


def main(argumentos: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    raiz = Path(argumentos[0]).resolve() if argumentos else RAIZ

    achados = varrer(raiz)
    if not achados:
        print("✅ Nenhuma chave de API encontrada nos arquivos.")
        return 0

    print("❌ Possível chave de API no repositório:\n", file=sys.stderr)
    for a in achados:
        print(f"  {a.arquivo}:{a.linha}  {a.tipo}  {a.inicio}", file=sys.stderr)
    print(
        "\nNada será publicado. Tire a chave do arquivo e, se ela era de verdade, "
        "revogue-a no provedor: ela já pode ter sido vista.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
