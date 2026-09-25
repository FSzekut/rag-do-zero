"""Leitura e validação do `config.yaml`.

Este módulo existe para transformar "errei a configuração" em uma mensagem clara,
em vez de um site quebrado. Ele não conhece Gradio nem provedor de IA: só lê o
arquivo, confere campo por campo e devolve um objeto pronto para uso.

Duas decisões de projeto que valem a explicação:

1. **Todos os erros de uma vez.** Um validador que para no primeiro problema
   obriga a corrigir, publicar, descobrir o próximo, corrigir de novo. Aqui a
   lista sai inteira.
2. **Campo desconhecido é erro, não silêncio.** Escrever `cor_primária` com
   acento e ver a cor simplesmente não mudar é o tipo de erro que consome uma
   tarde. Melhor recusar e dizer o nome certo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROVEDORES_ACEITOS = ("openrouter", "anthropic", "openai")
TEMAS_ACEITOS = ("claro", "escuro")
EXTENSOES_DE_LOGO = (".png", ".jpg", ".svg")
COR_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class ErroDeConfiguracao(Exception):
    """Erro de configuração, com a lista completa do que precisa ser corrigido."""

    def __init__(self, erros: list[str]) -> None:
        self.erros = erros
        corpo = "\n".join(f"  - {e}" for e in erros)
        plural = "problema" if len(erros) == 1 else "problemas"
        super().__init__(f"{len(erros)} {plural} no config.yaml:\n{corpo}")


@dataclass(frozen=True)
class Assistente:
    nome: str
    descricao: str
    logo: str = ""
    logo_altura_px: int = 64


@dataclass(frozen=True)
class Aparencia:
    cor_primaria: str
    cor_secundaria: str = ""
    tema: str = "claro"


@dataclass(frozen=True)
class Comportamento:
    papel: str
    publico: str = ""
    proibicoes: list[str] = field(default_factory=list)
    mensagem_boas_vindas: str = ""


@dataclass(frozen=True)
class Limites:
    tamanho_maximo_resposta: int = 800
    mensagens_por_sessao: int = 20


@dataclass(frozen=True)
class Provedor:
    nome: str
    modelo: str


@dataclass(frozen=True)
class Config:
    assistente: Assistente
    aparencia: Aparencia
    comportamento: Comportamento
    limites: Limites
    provedores: list[Provedor]
    perguntas_exemplo: list[str] = field(default_factory=list)


class _Coletor:
    """Junta os erros em vez de parar no primeiro."""

    def __init__(self) -> None:
        self.erros: list[str] = []

    def erro(self, campo: str, motivo: str) -> None:
        self.erros.append(f"{campo}: {motivo}")

    # -- verificações reaproveitadas ------------------------------------------

    def bloco(self, dados: Any, campo: str, obrigatorio: bool) -> dict[str, Any]:
        if dados is None:
            if obrigatorio:
                self.erro(campo, "bloco obrigatório ausente")
            return {}
        if not isinstance(dados, dict):
            self.erro(campo, "deveria ser um bloco de campos, não um valor solto")
            return {}
        return dados

    def sem_campos_extras(self, dados: dict[str, Any], campo: str,
                          conhecidos: tuple[str, ...]) -> None:
        for chave in dados:
            if chave not in conhecidos:
                aceitos = ", ".join(conhecidos)
                self.erro(
                    f"{campo}.{chave}",
                    f"campo desconhecido — os aceitos aqui são: {aceitos}",
                )

    def texto(self, dados: dict[str, Any], campo: str, chave: str, *,
              obrigatorio: bool, minimo: int = 0, maximo: int = 10_000,
              padrao: str = "") -> str:
        valor = dados.get(chave)
        caminho = f"{campo}.{chave}"
        if valor is None or valor == "":
            if obrigatorio:
                self.erro(caminho, "campo obrigatório vazio ou ausente")
                return ""
            return padrao
        if not isinstance(valor, str):
            self.erro(caminho, "deveria ser texto, entre aspas")
            return padrao
        limpo = valor.strip()
        if len(limpo) < minimo:
            self.erro(caminho, f"curto demais (mínimo de {minimo} caracteres)")
        if len(limpo) > maximo:
            self.erro(caminho, f"longo demais (máximo de {maximo} caracteres)")
        return limpo

    def inteiro(self, dados: dict[str, Any], campo: str, chave: str, *,
                minimo: int, maximo: int, padrao: int) -> int:
        valor = dados.get(chave)
        caminho = f"{campo}.{chave}"
        if valor is None:
            return padrao
        if isinstance(valor, bool) or not isinstance(valor, int):
            self.erro(caminho, "deveria ser um número inteiro, sem aspas")
            return padrao
        if not minimo <= valor <= maximo:
            self.erro(caminho, f"fora da faixa aceita, de {minimo} a {maximo}")
        return valor

    def cor(self, dados: dict[str, Any], campo: str, chave: str, *,
            obrigatorio: bool) -> str:
        valor = self.texto(dados, campo, chave, obrigatorio=obrigatorio, maximo=7)
        if not valor:
            return ""
        if not COR_HEX.match(valor):
            self.erro(
                f"{campo}.{chave}",
                f'"{valor}" não é uma cor hexadecimal — use #RGB ou #RRGGBB, '
                'por exemplo "#1f6feb"',
            )
        return valor

    def escolha(self, dados: dict[str, Any], campo: str, chave: str, *,
                opcoes: tuple[str, ...], padrao: str) -> str:
        valor = dados.get(chave)
        if valor is None or valor == "":
            return padrao
        if valor not in opcoes:
            self.erro(
                f"{campo}.{chave}",
                f'"{valor}" não é aceito — use {" ou ".join(opcoes)}',
            )
            return padrao
        return valor

    def lista_de_textos(self, dados: dict[str, Any], campo: str, chave: str, *,
                        maximo_de_itens: int, maximo_por_item: int) -> list[str]:
        valor = dados.get(chave)
        caminho = f"{campo}.{chave}" if campo else chave
        if valor is None:
            return []
        if not isinstance(valor, list):
            self.erro(caminho, "deveria ser uma lista, com um hífen por item")
            return []
        if len(valor) > maximo_de_itens:
            self.erro(caminho, f"no máximo {maximo_de_itens} itens")
        itens: list[str] = []
        for i, item in enumerate(valor, start=1):
            if not isinstance(item, str) or not item.strip():
                self.erro(f"{caminho}[{i}]", "deveria ser um texto não vazio")
                continue
            if len(item.strip()) > maximo_por_item:
                self.erro(
                    f"{caminho}[{i}]",
                    f"longo demais (máximo de {maximo_por_item} caracteres)",
                )
            itens.append(item.strip())
        return itens


def _validar_logo(c: _Coletor, caminho_logo: str, raiz: Path) -> str:
    if not caminho_logo:
        return ""
    if not caminho_logo.lower().endswith(EXTENSOES_DE_LOGO):
        aceitas = ", ".join(EXTENSOES_DE_LOGO)
        c.erro("assistente.logo", f"extensão não aceita — use uma de: {aceitas}")
        return caminho_logo
    if not (raiz / caminho_logo).is_file():
        c.erro(
            "assistente.logo",
            f'o arquivo "{caminho_logo}" não existe — confira se ele foi commitado',
        )
    return caminho_logo


def _validar_provedores(c: _Coletor, dados: Any) -> list[Provedor]:
    if dados is None:
        c.erro("provedores", "campo obrigatório ausente — declare ao menos um provedor")
        return []
    if not isinstance(dados, list) or not dados:
        c.erro("provedores", "deveria ser uma lista com ao menos um item")
        return []

    provedores: list[Provedor] = []
    vistos: set[str] = set()
    for i, item in enumerate(dados, start=1):
        caminho = f"provedores[{i}]"
        if not isinstance(item, dict):
            c.erro(caminho, "deveria ter os campos nome e modelo")
            continue
        c.sem_campos_extras(item, caminho, ("nome", "modelo"))
        nome = item.get("nome")
        modelo = item.get("modelo")
        if nome not in PROVEDORES_ACEITOS:
            aceitos = ", ".join(PROVEDORES_ACEITOS)
            c.erro(f"{caminho}.nome", f'"{nome}" não é aceito — use um de: {aceitos}')
            continue
        if nome in vistos:
            c.erro(f"{caminho}.nome", f'"{nome}" aparece mais de uma vez')
            continue
        if not isinstance(modelo, str) or not modelo.strip():
            c.erro(f"{caminho}.modelo", "campo obrigatório vazio ou ausente")
            continue
        vistos.add(nome)
        provedores.append(Provedor(nome=nome, modelo=modelo.strip()))
    return provedores


def interpretar(dados: Any, raiz: Path) -> Config:
    """Valida um dicionário já lido do YAML e devolve a configuração pronta.

    `raiz` é a pasta usada para procurar a logo.
    """
    c = _Coletor()
    if not isinstance(dados, dict):
        raise ErroDeConfiguracao(["arquivo: o conteúdo não é um bloco de campos YAML"])

    c.sem_campos_extras(
        dados,
        "raiz",
        ("assistente", "aparencia", "comportamento", "perguntas_exemplo",
         "limites", "provedores"),
    )

    b_assistente = c.bloco(dados.get("assistente"), "assistente", obrigatorio=True)
    c.sem_campos_extras(
        b_assistente, "assistente", ("nome", "descricao", "logo", "logo_altura_px")
    )
    logo = c.texto(b_assistente, "assistente", "logo", obrigatorio=False)
    assistente = Assistente(
        nome=c.texto(
            b_assistente, "assistente", "nome", obrigatorio=True, minimo=1, maximo=60
        ),
        descricao=c.texto(
            b_assistente, "assistente", "descricao",
            obrigatorio=True, minimo=1, maximo=200,
        ),
        logo=_validar_logo(c, logo, raiz),
        logo_altura_px=c.inteiro(
            b_assistente, "assistente", "logo_altura_px",
            minimo=16, maximo=200, padrao=64,
        ),
    )

    b_aparencia = c.bloco(dados.get("aparencia"), "aparencia", obrigatorio=True)
    c.sem_campos_extras(
        b_aparencia, "aparencia", ("cor_primaria", "cor_secundaria", "tema")
    )
    aparencia = Aparencia(
        cor_primaria=c.cor(b_aparencia, "aparencia", "cor_primaria", obrigatorio=True),
        cor_secundaria=c.cor(
            b_aparencia, "aparencia", "cor_secundaria", obrigatorio=False
        ),
        tema=c.escolha(
            b_aparencia, "aparencia", "tema", opcoes=TEMAS_ACEITOS, padrao="claro"
        ),
    )

    b_comp = c.bloco(dados.get("comportamento"), "comportamento", obrigatorio=True)
    c.sem_campos_extras(
        b_comp,
        "comportamento",
        ("papel", "publico", "proibicoes", "mensagem_boas_vindas"),
    )
    comportamento = Comportamento(
        papel=c.texto(
            b_comp, "comportamento", "papel", obrigatorio=True, minimo=10, maximo=2000
        ),
        publico=c.texto(b_comp, "comportamento", "publico", obrigatorio=False,
                        maximo=300),
        proibicoes=c.lista_de_textos(
            b_comp, "comportamento", "proibicoes",
            maximo_de_itens=10, maximo_por_item=300,
        ),
        mensagem_boas_vindas=c.texto(
            b_comp, "comportamento", "mensagem_boas_vindas",
            obrigatorio=False, maximo=300,
        ),
    )

    b_limites = c.bloco(dados.get("limites"), "limites", obrigatorio=False)
    c.sem_campos_extras(
        b_limites, "limites", ("tamanho_maximo_resposta", "mensagens_por_sessao")
    )
    limites = Limites(
        tamanho_maximo_resposta=c.inteiro(
            b_limites, "limites", "tamanho_maximo_resposta",
            minimo=100, maximo=4000, padrao=800,
        ),
        mensagens_por_sessao=c.inteiro(
            b_limites, "limites", "mensagens_por_sessao",
            minimo=1, maximo=200, padrao=20,
        ),
    )

    perguntas = c.lista_de_textos(
        dados, "", "perguntas_exemplo", maximo_de_itens=6, maximo_por_item=120
    )
    provedores = _validar_provedores(c, dados.get("provedores"))

    if c.erros:
        raise ErroDeConfiguracao(c.erros)

    return Config(
        assistente=assistente,
        aparencia=aparencia,
        comportamento=comportamento,
        limites=limites,
        provedores=provedores,
        perguntas_exemplo=perguntas,
    )


def carregar(caminho: str | Path = "config.yaml") -> Config:
    """Lê o arquivo do disco, valida e devolve a configuração.

    A logo é procurada a partir da pasta onde o próprio arquivo está.
    """
    arquivo = Path(caminho)
    if not arquivo.is_file():
        raise ErroDeConfiguracao([f'arquivo: "{arquivo}" não foi encontrado'])
    try:
        dados = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    except yaml.YAMLError as erro:
        raise ErroDeConfiguracao(
            [f"arquivo: o YAML está mal formado — {erro}"]
        ) from erro
    return interpretar(dados, raiz=arquivo.parent)
