"""A tela do chat, montada a partir do `config.yaml`.

Duas camadas, de propósito:

1. **Funções puras** (`css_do_tema`, `cabecalho_html`, `conversar`...): recebem a
   configuração e devolvem texto ou listas. Dá para testar sem abrir navegador e
   sem chave de API.
2. **`montar`**: a única que conhece o Gradio. Só cola as peças da camada 1.

Duas decisões que valem a explicação:

- **O limite de mensagens mora no histórico.** O `gr.Chatbot` guarda a conversa
  por aba do navegador, então "mensagens por sessão" é só contar quantas vezes o
  usuário já escreveu ali. Recarregar a aba zera, exatamente como o `config.yaml`
  promete.
- **A mensagem de boas-vindas não vai para o modelo.** Ela aparece na tela como
  se o assistente a tivesse dito, mas a Anthropic exige que a conversa comece
  por uma mensagem do usuário. `mensagens_para_o_modelo` descarta o que vem
  antes da primeira pergunta.
"""

from __future__ import annotations

import base64
import html
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .config import Config
from .provedores import Resposta, responder

TIPOS_DE_LOGO = {".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml"}

AVISO_DE_LIMITE = (
    "Chegamos ao limite de {limite} mensagens desta conversa, que existe para "
    "controlar o custo. **Recarregue a página** para começar uma nova."
)

Mensagem = dict[str, Any]
Respondedor = Callable[[Config, Sequence[Mapping[str, str]]], Resposta]


# -- aparência ---------------------------------------------------------------


def _componentes_rgb(cor: str) -> tuple[int, int, int]:
    """`#RGB` ou `#RRGGBB` viram três inteiros de 0 a 255."""
    digitos = cor.lstrip("#")
    if len(digitos) == 3:
        digitos = "".join(letra * 2 for letra in digitos)
    return int(digitos[0:2], 16), int(digitos[2:4], 16), int(digitos[4:6], 16)


def cor_do_texto_sobre(fundo: str) -> str:
    """Branco sobre fundo escuro, preto sobre fundo claro.

    Quem escolhe `cor_primaria: "#ffeb3b"` (amarelo) não deveria ganhar botões
    com letra branca ilegível.
    """
    vermelho, verde, azul = _componentes_rgb(fundo)
    luminosidade = 0.299 * vermelho + 0.587 * verde + 0.114 * azul
    return "#111111" if luminosidade > 160 else "#ffffff"


def css_do_tema(config: Config) -> str:
    """O CSS que aplica as cores do `config.yaml`.

    As cores já chegaram validadas como hexadecimais, então entram no CSS sem
    risco de injeção.
    """
    primaria = config.aparencia.cor_primaria
    secundaria = config.aparencia.cor_secundaria
    texto_botao = cor_do_texto_sobre(primaria)
    fundo_do_topo = secundaria or "transparent"
    cor_do_titulo = cor_do_texto_sobre(secundaria) if secundaria else primaria

    return f"""
:root, .dark {{
  --button-primary-background-fill: {primaria};
  --button-primary-background-fill-hover: {primaria};
  --button-primary-border-color: {primaria};
  --button-primary-text-color: {texto_botao};
  --color-accent: {primaria};
  --link-text-color: {primaria};
  --link-text-color-hover: {primaria};
}}
.cabecalho {{
  display: flex; align-items: center; gap: 16px;
  padding: 16px 20px; border-radius: 12px;
  background: {fundo_do_topo};
}}
.cabecalho h1 {{ margin: 0; font-size: 1.5rem; color: {cor_do_titulo}; }}
.cabecalho p {{ margin: 4px 0 0; color: {cor_do_titulo}; opacity: 0.85; }}
.cabecalho img {{ width: auto; }}
"""


def js_do_tema(config: Config) -> str:
    """Força o tema escolhido, em vez de seguir o do sistema do visitante."""
    acao = "add" if config.aparencia.tema == "escuro" else "remove"
    return f"() => {{ document.body.classList.{acao}('dark'); }}"


def logo_como_data_uri(config: Config, raiz: Path) -> str:
    """Embute a logo no próprio HTML, para não depender de servir arquivos."""
    if not config.assistente.logo:
        return ""
    arquivo = raiz / config.assistente.logo
    tipo = TIPOS_DE_LOGO.get(arquivo.suffix.lower())
    if tipo is None or not arquivo.is_file():
        return ""
    conteudo = base64.b64encode(arquivo.read_bytes()).decode("ascii")
    return f"data:{tipo};base64,{conteudo}"


def cabecalho_html(config: Config, raiz: Path) -> str:
    """Logo (se houver), nome e descrição no topo da tela."""
    logo = logo_como_data_uri(config, raiz)
    altura = config.assistente.logo_altura_px
    imagem = f'<img src="{logo}" alt="" style="height: {altura}px">' if logo else ""
    nome = html.escape(config.assistente.nome)
    descricao = html.escape(config.assistente.descricao)
    return (
        f'<header class="cabecalho">{imagem}'
        f"<div><h1>{nome}</h1><p>{descricao}</p></div></header>"
    )


# -- conversa ----------------------------------------------------------------


def _texto_da_mensagem(conteudo: Any) -> str:
    """O Gradio pode entregar o conteúdo como texto ou como lista de partes."""
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        partes = []
        for parte in conteudo:
            if isinstance(parte, str):
                partes.append(parte)
            elif isinstance(parte, dict) and isinstance(parte.get("text"), str):
                partes.append(parte["text"])
        return "".join(partes)
    return ""


def mensagens_para_o_modelo(historico: Sequence[Mensagem]) -> list[dict[str, str]]:
    """Reduz o histórico do Gradio ao que o modelo precisa: `role` e `content`.

    Descarta a mensagem de boas-vindas (tudo que vem antes da primeira pergunta).
    """
    mensagens: list[dict[str, str]] = []
    for item in historico:
        papel = item.get("role")
        texto = _texto_da_mensagem(item.get("content"))
        if papel in ("user", "assistant") and texto.strip():
            mensagens.append({"role": papel, "content": texto})
    while mensagens and mensagens[0]["role"] == "assistant":
        mensagens.pop(0)
    return mensagens


def conversar(
    config: Config,
    historico: Sequence[Mensagem] | None,
    texto: str | None,
    *,
    responder_fn: Respondedor = responder,
) -> list[Mensagem]:
    """Acrescenta a pergunta e a resposta ao histórico e devolve o novo histórico.

    `responder_fn` existe para os testes injetarem um dublê.

    Quando a resposta falha (todos os provedores fora do ar, ou nenhuma chave), o
    aviso entra no histórico como uma fala do assistente. Fica no contexto das
    próximas perguntas, o que é um custo pequeno e aceito: o modelo ignora.
    """
    novo: list[Mensagem] = list(historico or [])
    pergunta = (texto or "").strip()
    if not pergunta:
        return novo

    ja_perguntadas = sum(1 for m in novo if m.get("role") == "user")
    novo.append({"role": "user", "content": pergunta})

    limite = config.limites.mensagens_por_sessao
    if ja_perguntadas >= limite:
        novo.append(
            {"role": "assistant", "content": AVISO_DE_LIMITE.format(limite=limite)}
        )
        return novo

    resposta = responder_fn(config, mensagens_para_o_modelo(novo))
    novo.append({"role": "assistant", "content": resposta.texto})
    return novo


# -- a tela, com o Gradio ----------------------------------------------------


def opcoes_de_lancamento(config: Config) -> dict[str, Any]:
    """O que o Gradio 6 pede em `launch()`: tema, CSS e JavaScript.

    (Nas versões anteriores isso ia no construtor do `Blocks`.)
    """
    import gradio as gr

    return {
        "theme": gr.themes.Base(),
        "css": css_do_tema(config),
        "js": js_do_tema(config),
    }


def montar(config: Config, raiz: Path, *, responder_fn: Respondedor = responder):
    """Monta a tela inteira e devolve o `gr.Blocks`, ainda sem publicar."""
    import gradio as gr

    boas_vindas = config.comportamento.mensagem_boas_vindas
    inicial: list[Mensagem] = (
        [{"role": "assistant", "content": boas_vindas}] if boas_vindas else []
    )

    with gr.Blocks(title=config.assistente.nome) as tela:
        gr.HTML(cabecalho_html(config, raiz))
        conversa = gr.Chatbot(value=inicial, height=480, show_label=False)
        caixa = gr.Textbox(
            placeholder="Escreva sua pergunta e tecle Enter",
            show_label=False,
            submit_btn=True,
            autofocus=True,
        )

        def enviar(texto: str, historico: list[Mensagem]):
            return conversar(config, historico, texto, responder_fn=responder_fn), ""

        caixa.submit(enviar, [caixa, conversa], [conversa, caixa])

        if config.perguntas_exemplo:
            gr.Markdown("**Experimente perguntar:**")
            for pergunta in config.perguntas_exemplo:

                def perguntar(historico: list[Mensagem], pergunta: str = pergunta):
                    return conversar(
                        config, historico, pergunta, responder_fn=responder_fn
                    )

                gr.Button(pergunta, size="sm").click(perguntar, [conversa], [conversa])

    return tela
