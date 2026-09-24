"""Ponto de entrada. O encanamento está pronto; as etapas é que faltam.

    python -m rag.cli ingest
    python -m rag.cli ask "sua pergunta"
"""

from __future__ import annotations

import argparse
import sys

from . import config


def cmd_ingest() -> int:
    from .index import build_index
    from .ingest import load_documents, split_documents

    documents = load_documents()
    if not documents:
        print(f"Nenhum arquivo suportado em {config.RAW_DIR}", file=sys.stderr)
        return 1

    chunks = split_documents(documents)
    build_index(chunks)
    print(f"{len(documents)} documentos -> {len(chunks)} chunks em {config.CHROMA_DIR}")
    return 0


def cmd_ask(question: str) -> int:
    from .answer import answer

    resposta, fontes = answer(question)
    print(resposta)
    print("\nFontes:")
    for doc in fontes:
        origem = doc.metadata.get("source", "?")
        pagina = doc.metadata.get("page")
        print(f"  - {origem}" + (f", p. {pagina}" if pagina is not None else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rag", description="RAG do zero")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="lê data/raw/ e (re)constrói o índice")
    ask = sub.add_parser("ask", help="pergunta ao índice já construído")
    ask.add_argument("question")

    args = parser.parse_args(argv)
    if args.command == "ingest":
        return cmd_ingest()
    return cmd_ask(args.question)


if __name__ == "__main__":
    raise SystemExit(main())
