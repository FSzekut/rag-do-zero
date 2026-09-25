---
title: Professor Eng Dados
emoji: 🌖
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.28.0
python_version: '3.12'
app_file: app.py
pinned: false
---

# Professor de Engenharia de Dados

Assistente de IA que tira dúvidas de engenharia de dados e inteligência artificial,
explicando como professor. Publicado em
[huggingface.co/spaces/FSzekut/professor-eng-dados](https://huggingface.co/spaces/FSzekut/professor-eng-dados).

> **O bloco entre `---` no topo deste arquivo não é enfeite.** É ele que diz ao Hugging
> Face qual SDK usar, qual versão e qual arquivo executar. Apagar essas linhas quebra a
> publicação.

## O que é este repositório

Projeto da pós **Engenharia de Dados e IA** (Anhanguera), construído em partes:

| Parte | O que entrega | Situação |
|---|---|---|
| 1 | Chat publicado + esteira automática de CI/CD | em construção |
| 2 | Base de conhecimento com documentos próprios (RAG) | a fazer |
| 3 | Site próprio, com domínio e visual feito do zero | a fazer |

O combinado da parte 1 está em [`SPEC-parte1-cicd-deploy.md`](SPEC-parte1-cicd-deploy.md);
a ideia original, em linguagem simples, em [`ideia_1.md`](ideia_1.md).

## Como personalizar o assistente

Editando **um arquivo só**, o `config.yaml`, direto pelo site do GitHub: nome, descrição,
cores, logo, instruções de comportamento, perguntas de exemplo, limites e quais modelos
usar, em ordem de preferência. Ao salvar, a esteira confere a alteração e o site se
atualiza sozinho. Se a configuração estiver errada, a publicação é barrada e a versão
anterior continua no ar.

## Chaves de API

O assistente funciona com **qualquer uma** destas três, sozinha ou combinadas:

| Provedor | Variável | Observação |
|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | dá acesso a modelos gratuitos; é o primeiro da fila |
| Anthropic | `ANTHROPIC_API_KEY` | |
| OpenAI | `OPENAI_API_KEY` | |

As chaves ficam **só nos Secrets do Space**, nunca no código. Se um provedor falhar antes
de responder, o app tenta o próximo sozinho.

## Rodando no meu computador

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt
pytest
```

Os testes rodam **sem chave de API e sem internet** — de propósito, para o portão do CI
ser rápido e nunca precisar de segredo.
