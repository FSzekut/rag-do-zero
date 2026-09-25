"""A fila de provedores de IA e a troca automática entre eles.

A regra em uma frase: **tenta na ordem do `config.yaml`, pulando quem não tem
chave, e cai para o próximo quando um falha antes de responder.**

O que conta como "falhar antes de responder": chave inválida (401/403), sem
crédito (402), limite atingido ou modelo gratuito lotado (429), provedor fora do
ar (5xx), tempo esgotado e falha de conexão. Se o provedor já entregou texto, a
resposta é dele e ninguém mais é chamado.

Este módulo nunca levanta exceção para quem o chama. Mesmo o pior caso — nenhuma
chave cadastrada, ou todos falharem — vira uma `Resposta` com texto explicando o
que aconteceu, porque quem está do outro lado é um usuário no chat, não um
programador lendo log.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from .config import Config, Provedor

VARIAVEL_DE_CHAVE = {
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}
URL_DO_OPENROUTER = "https://openrouter.ai/api/v1"

# Formatos de chave que nunca podem aparecer numa mensagem de erro.
FORMATO_DE_CHAVE = re.compile(r"\b(?:sk|hf|sk-or|sk-ant)[-_][A-Za-z0-9_\-]{8,}")


@dataclass(frozen=True)
class Tentativa:
    """O que aconteceu com um provedor da fila."""

    provedor: str
    modelo: str
    ok: bool
    motivo: str = ""


@dataclass(frozen=True)
class Resposta:
    """O resultado final, com o rastro de tudo que foi tentado."""

    texto: str
    provedor: str | None
    modelo: str | None
    tentativas: list[Tentativa]

    @property
    def deu_certo(self) -> bool:
        return self.provedor is not None


class FalhaDoProvedor(Exception):
    """Falha antes de responder — dá para tentar o próximo da fila."""


class Cliente(Protocol):
    """O mínimo que a fila precisa saber sobre um provedor.

    É o que permite testar a troca automática sem chave e sem internet: nos
    testes entra um dublê que falha de propósito.
    """

    def conversar(
        self,
        modelo: str,
        instrucao: str,
        mensagens: Sequence[Mapping[str, str]],
        limite_de_tokens: int,
    ) -> str: ...


class ClienteAnthropic:
    """Fala com a Anthropic pelo SDK oficial `anthropic`."""

    def __init__(self, chave: str) -> None:
        import anthropic

        self._cliente = anthropic.Anthropic(api_key=chave)

    def conversar(self, modelo, instrucao, mensagens, limite_de_tokens) -> str:
        resposta = self._cliente.messages.create(
            model=modelo,
            max_tokens=limite_de_tokens,
            system=instrucao,
            messages=[dict(m) for m in mensagens],
        )
        if getattr(resposta, "stop_reason", None) == "refusal":
            raise FalhaDoProvedor("o modelo recusou responder a esta pergunta")
        partes = [
            bloco.text
            for bloco in resposta.content
            if getattr(bloco, "type", "") == "text"
        ]
        return "\n".join(partes)


class ClienteOpenAI:
    """Fala com a OpenAI e com o OpenRouter, que usa a mesma API.

    A única diferença entre os dois é o `base_url` e o nome do parâmetro que
    limita o tamanho da resposta: a OpenAI pede `max_completion_tokens` nos
    modelos novos, e o OpenRouter espera `max_tokens`.
    """

    def __init__(
        self, chave: str, *, base_url: str | None = None, parametro_de_limite: str
    ) -> None:
        import openai

        self._cliente = openai.OpenAI(api_key=chave, base_url=base_url)
        self._parametro_de_limite = parametro_de_limite

    def conversar(self, modelo, instrucao, mensagens, limite_de_tokens) -> str:
        resposta = self._cliente.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": instrucao},
                *[dict(m) for m in mensagens],
            ],
            **{self._parametro_de_limite: limite_de_tokens},
        )
        return resposta.choices[0].message.content or ""


def criar_cliente(nome: str, chave: str) -> Cliente:
    """Devolve o cliente certo para cada provedor."""
    if nome == "anthropic":
        return ClienteAnthropic(chave)
    if nome == "openrouter":
        return ClienteOpenAI(
            chave, base_url=URL_DO_OPENROUTER, parametro_de_limite="max_tokens"
        )
    if nome == "openai":
        return ClienteOpenAI(chave, parametro_de_limite="max_completion_tokens")
    raise FalhaDoProvedor(f'provedor "{nome}" não tem cliente implementado')


def instrucao_do_sistema(config: Config) -> str:
    """Costura os campos de `comportamento` no texto enviado ao modelo.

    O usuário do chat nunca vê este texto.
    """
    partes = [config.comportamento.papel.strip()]
    if config.comportamento.publico:
        partes.append(f"Seu público: {config.comportamento.publico}")
    if config.comportamento.proibicoes:
        regras = "\n".join(f"- {r}" for r in config.comportamento.proibicoes)
        partes.append(f"Regras que você precisa respeitar:\n{regras}")
    partes.append("Responda sempre em português do Brasil.")
    return "\n\n".join(partes)


def disponiveis(
    provedores: Sequence[Provedor], ambiente: Mapping[str, str]
) -> list[Provedor]:
    """Filtra a fila, deixando só quem tem chave cadastrada no ambiente."""
    return [
        p
        for p in provedores
        if (ambiente.get(VARIAVEL_DE_CHAVE[p.nome]) or "").strip()
    ]


# Abaixo disto não é chave de verdade, e trocar cega o texto: uma "chave" de uma
# letra transformaria "não encontrado" em "não encontr***do".
TAMANHO_MINIMO_DE_CHAVE = 8


def _sem_segredo(texto: str, chaves: Sequence[str]) -> str:
    """Tira qualquer chave do texto antes de ele chegar à tela."""
    limpo = texto
    for chave in chaves:
        if chave and len(chave) >= TAMANHO_MINIMO_DE_CHAVE:
            limpo = limpo.replace(chave, "***")
    return FORMATO_DE_CHAVE.sub("***", limpo)


def _motivo_legivel(erro: Exception) -> str:
    """Traduz a falha para uma frase que o usuário do chat entende."""
    if isinstance(erro, FalhaDoProvedor):
        return str(erro)

    status = getattr(erro, "status_code", None)
    if status in (401, 403):
        return f"chave inválida ou sem permissão ({status})"
    if status == 402:
        return "sem crédito no provedor (402)"
    if status == 404:
        return "modelo não encontrado neste provedor (404)"
    if status == 429:
        return "limite atingido ou modelo gratuito lotado (429)"
    if isinstance(status, int) and status >= 500:
        return f"provedor fora do ar ({status})"

    nome = type(erro).__name__.lower()
    if "timeout" in nome:
        return "o provedor demorou demais para responder"
    if "connection" in nome or "apiconnection" in nome:
        return "não foi possível conectar ao provedor"
    return f"{type(erro).__name__}: {erro}"


def _texto_sem_chave_nenhuma(config: Config) -> str:
    variaveis = "\n".join(
        f"- `{VARIAVEL_DE_CHAVE[p.nome]}` para usar {p.nome}"
        for p in config.provedores
    )
    return (
        "Nenhuma chave de API está cadastrada, então ainda não consigo responder.\n\n"
        "Para me ligar, crie **um** destes segredos nas configurações do Space "
        f"(*Settings → Variables and secrets*):\n{variaveis}\n\n"
        "Basta uma delas. O nome precisa estar exatamente assim, sem abreviar."
    )


def _texto_de_falha_geral(tentativas: Sequence[Tentativa]) -> str:
    linhas = "\n".join(
        f"- **{t.provedor}** (`{t.modelo}`): {t.motivo}" for t in tentativas
    )
    return (
        "Tentei todos os provedores configurados e nenhum conseguiu responder "
        f"agora:\n\n{linhas}\n\nTente de novo em alguns minutos."
    )


def responder(
    config: Config,
    mensagens: Sequence[Mapping[str, str]],
    *,
    ambiente: Mapping[str, str] | None = None,
    fabrica=criar_cliente,
) -> Resposta:
    """Pergunta ao primeiro provedor que puder responder.

    `mensagens` é o histórico no formato `{"role": "user"|"assistant",
    "content": "..."}`. `fabrica` existe para os testes injetarem um dublê.
    """
    ambiente = os.environ if ambiente is None else ambiente
    fila = disponiveis(config.provedores, ambiente)
    if not fila:
        return Resposta(_texto_sem_chave_nenhuma(config), None, None, [])

    instrucao = instrucao_do_sistema(config)
    chaves = [ambiente.get(VARIAVEL_DE_CHAVE[p.nome], "") for p in fila]
    tentativas: list[Tentativa] = []

    for provedor, chave in zip(fila, chaves, strict=True):
        try:
            cliente = fabrica(provedor.nome, chave)
            texto = cliente.conversar(
                provedor.modelo,
                instrucao,
                mensagens,
                config.limites.tamanho_maximo_resposta,
            )
            if not texto.strip():
                raise FalhaDoProvedor("o provedor devolveu uma resposta vazia")
        except Exception as erro:  # a falha de um não pode derrubar a fila
            motivo = _sem_segredo(_motivo_legivel(erro), chaves)
            tentativas.append(Tentativa(provedor.nome, provedor.modelo, False, motivo))
            continue

        tentativas.append(Tentativa(provedor.nome, provedor.modelo, True))
        return Resposta(texto, provedor.nome, provedor.modelo, tentativas)

    return Resposta(_texto_de_falha_geral(tentativas), None, None, tentativas)
