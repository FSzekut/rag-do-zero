"""Dividir os documentos em trechos (RF19 a RF21).

Um **trecho** é a unidade que a busca encontra. Dividir bem é metade da qualidade
do RAG: trecho grande demais mistura assuntos e dilui o vetor; pequeno demais
perde o contexto.

A estratégia é a "por estrutura", a mais subestimada segundo a apostila: cada
título do Markdown abre uma seção, e a seção é o trecho. Só a seção que passa do
`tamanho` é subdividida, por parágrafo, com um pouco de sobreposição.

Três regras que valem sempre:

1. **Código e tabela nunca são partidos.** Um bloco de código cortado ao meio, ou
   uma tabela sem o cabeçalho, não responde pergunta nenhuma. Se um bloco sozinho
   passa do tamanho, ele vira um trecho maior que o limite: é o mal menor.
2. **`#` dentro de bloco de código não é título.** Os exemplos de YAML e de prompt
   das apostilas estão cheios de linhas começando com `#`.
3. **O título do documento (o `#` de nível 1) não entra no caminho da seção.** Ele
   se repetiria em todos os trechos e não ajudaria a distinguir nenhum. Quem
   identifica o documento é a `fonte`.

Este módulo é puro: recebe texto, devolve trechos. Não conhece banco nem modelo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TITULO = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
CERCA = re.compile(r"^\s*(`{3,}|~{3,})")
FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+")
SEPARADOR_DE_TITULOS = " > "


@dataclass(frozen=True)
class Trecho:
    """Um pedaço de documento, pronto para virar vetor e ser achado."""

    fonte: str  # nome do arquivo, ex.: "parte2-rag.md"
    secao: str  # caminho dos títulos, ex.: "07 Tipos de embeddings > Bi-encoder"
    ordem: int  # posição do trecho no documento, a partir de 0
    conteudo: str

    @property
    def palavras(self) -> int:
        return len(self.conteudo.split())

    @property
    def texto_para_embedding(self) -> str:
        """O que vai ao modelo de embedding: começa pelo título da seção (RF21).

        Assim um trecho cujo parágrafo só fala de "HF_TOKEN" ainda é achado por uma
        pergunta sobre o assunto do título ("onde ficam os segredos?").
        """
        return f"{self.secao}\n\n{self.conteudo}" if self.secao else self.conteudo


@dataclass(frozen=True)
class _Bloco:
    tipo: str  # "paragrafo", "tabela" ou "codigo"
    texto: str
    # frase que continua o parágrafo da anterior: une com espaço, não com \n\n
    continua: bool = False

    @property
    def palavras(self) -> int:
        return len(self.texto.split())

    @property
    def indivisivel(self) -> bool:
        return self.tipo in ("tabela", "codigo")


@dataclass
class _Secao:
    caminho: str
    blocos: list[_Bloco]


# -- leitura do Markdown -------------------------------------------------------


def _ler_secoes(markdown: str) -> list[_Secao]:
    """Quebra o documento em seções, cada uma com seus blocos.

    O texto antes do primeiro título (depois do `#` do documento) entra numa seção
    de caminho vazio.
    """
    secoes: list[_Secao] = [_Secao(caminho="", blocos=[])]
    pilha: dict[int, str] = {}  # nível -> título
    linhas = markdown.splitlines()
    i = 0
    paragrafo: list[str] = []

    def fechar_paragrafo() -> None:
        if paragrafo:
            secoes[-1].blocos.append(_Bloco("paragrafo", "\n".join(paragrafo)))
            paragrafo.clear()

    while i < len(linhas):
        linha = linhas[i]
        abertura = CERCA.match(linha)
        if abertura:  # bloco de código: vai até a cerca que fecha
            fechar_paragrafo()
            marca = abertura.group(1)[0] * 3
            bloco = [linha]
            i += 1
            while i < len(linhas):
                bloco.append(linhas[i])
                fecha = linhas[i].strip().startswith(marca)
                i += 1
                if fecha:
                    break
            secoes[-1].blocos.append(_Bloco("codigo", "\n".join(bloco)))
            continue

        titulo = TITULO.match(linha)
        if titulo:
            fechar_paragrafo()
            nivel, texto = len(titulo.group(1)), titulo.group(2).strip()
            for n in [n for n in pilha if n >= nivel]:
                del pilha[n]
            pilha[nivel] = texto
            # o título do documento (nível 1) não entra no caminho da seção
            caminho = SEPARADOR_DE_TITULOS.join(
                t for n, t in sorted(pilha.items()) if n > 1
            )
            secoes.append(_Secao(caminho=caminho, blocos=[]))
            i += 1
            continue

        if not linha.strip():
            fechar_paragrafo()
            i += 1
            continue

        if linha.lstrip().startswith("|"):  # tabela: linhas seguidas começando com |
            fechar_paragrafo()
            tabela = []
            while i < len(linhas) and linhas[i].lstrip().startswith("|"):
                tabela.append(linhas[i])
                i += 1
            secoes[-1].blocos.append(_Bloco("tabela", "\n".join(tabela)))
            continue

        paragrafo.append(linha)
        i += 1

    fechar_paragrafo()
    return [s for s in secoes if s.blocos]


# -- subdividir seção grande ----------------------------------------------------


def _frases(bloco: _Bloco) -> list[_Bloco]:
    """Parte um parágrafo grande em frases. Código e tabela ficam inteiros."""
    if bloco.indivisivel:
        return [bloco]
    partes = [p for p in FIM_DE_FRASE.split(bloco.texto) if p.strip()]
    if len(partes) <= 1:
        return [bloco]
    return [_Bloco("paragrafo", p, continua=i > 0) for i, p in enumerate(partes)]


def _juntar(blocos: list[_Bloco]) -> str:
    """Une os blocos: linha em branco entre eles; espaço entre frases do parágrafo."""
    texto = ""
    for i, bloco in enumerate(blocos):
        if i:
            texto += " " if bloco.continua else "\n\n"
        texto += bloco.texto
    return texto


def _cauda_para_sobreposicao(blocos: list[_Bloco], limite: int) -> list[_Bloco]:
    """Os últimos blocos de um trecho que cabem em `limite` palavras.

    Só entram blocos inteiros (uma frase ou um parágrafo curto): repetir meia frase
    seria pior que não repetir. Código e tabela nunca são repetidos.
    """
    cauda: list[_Bloco] = []
    total = 0
    for bloco in reversed(blocos):
        if bloco.indivisivel or total + bloco.palavras > limite:
            break
        cauda.insert(0, bloco)
        total += bloco.palavras
    return cauda


def _subdividir(blocos: list[_Bloco], tamanho: int, sobreposicao: int) -> list[str]:
    """Agrupa os blocos de uma seção em trechos de até `tamanho` palavras."""
    unidades: list[_Bloco] = []
    for bloco in blocos:
        if bloco.palavras > tamanho:
            unidades.extend(_frases(bloco))
        else:
            unidades.append(bloco)

    limite_da_cauda = tamanho * sobreposicao // 100
    trechos: list[str] = []
    atual: list[_Bloco] = []
    novos = 0  # palavras acrescentadas depois da sobreposição
    for unidade in unidades:
        total = sum(b.palavras for b in atual)
        if atual and total + unidade.palavras > tamanho and novos > 0:
            trechos.append(_juntar(atual))
            atual = _cauda_para_sobreposicao(atual, limite_da_cauda)
            if sum(b.palavras for b in atual) + unidade.palavras > tamanho:
                atual = []  # com a cauda o trecho passaria do limite: sem sobreposição
            novos = 0
        atual.append(unidade)
        novos += unidade.palavras
    if atual and novos > 0:
        trechos.append(_juntar(atual))
    return trechos


# -- interface pública ------------------------------------------------------------


def dividir_documento(
    markdown: str, *, fonte: str, tamanho: int = 150, sobreposicao: int = 15
) -> list[Trecho]:
    """Divide um documento Markdown em trechos (RF20).

    `tamanho` é o máximo de palavras por trecho; `sobreposicao`, o percentual
    repetido entre trechos vizinhos de uma mesma seção subdividida.
    """
    trechos: list[Trecho] = []
    for secao in _ler_secoes(markdown):
        total = sum(b.palavras for b in secao.blocos)
        if total <= tamanho:
            textos = [_juntar(secao.blocos)]
        else:
            textos = _subdividir(secao.blocos, tamanho, sobreposicao)
        for texto in textos:
            trechos.append(Trecho(fonte, secao.caminho, len(trechos), texto))
    return trechos


def dividir_pasta(
    pasta: Path, *, tamanho: int = 150, sobreposicao: int = 15
) -> list[Trecho]:
    """Divide todos os `.md` da pasta, em ordem alfabética."""
    trechos: list[Trecho] = []
    for arquivo in sorted(pasta.glob("*.md")):
        texto = arquivo.read_text(encoding="utf-8")
        trechos.extend(
            dividir_documento(
                texto, fonte=arquivo.name, tamanho=tamanho, sobreposicao=sobreposicao
            )
        )
    return trechos
