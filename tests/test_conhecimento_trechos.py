"""Testes da divisão em trechos — RF20 e RF21 da spec da parte 2.

Puros: texto entra, trechos saem. Sem banco, sem modelo, sem rede.
"""

from itertools import pairwise
from pathlib import Path

import pytest

from assistente.conhecimento.trechos import dividir_documento, dividir_pasta

RAIZ = Path(__file__).resolve().parent.parent

DOC = """# Título do documento

Texto antes do primeiro título.

## 01 Primeira

Texto um.

### Sub

Texto dois.

## 02 Segunda

Texto três.
"""


def secoes(trechos):
    return [(t.secao, t.conteudo) for t in trechos]


# -- dividir por título ---------------------------------------------------------


def test_cada_titulo_abre_um_trecho_com_o_caminho_da_secao():
    trechos = dividir_documento(DOC, fonte="doc.md")
    assert secoes(trechos) == [
        ("", "Texto antes do primeiro título."),
        ("01 Primeira", "Texto um."),
        ("01 Primeira > Sub", "Texto dois."),
        ("02 Segunda", "Texto três."),
    ]


def test_o_titulo_do_documento_nao_entra_no_caminho():
    trechos = dividir_documento(DOC, fonte="doc.md")
    assert not any("Título do documento" in t.secao for t in trechos)


def test_o_caminho_volta_um_nivel_quando_o_titulo_sobe():
    texto = "# D\n\n## A\n\n### A1\n\nx\n\n## B\n\ny\n"
    assert [t.secao for t in dividir_documento(texto, fonte="d.md")] == ["A > A1", "B"]


def test_fonte_e_ordem_acompanham_cada_trecho():
    trechos = dividir_documento(DOC, fonte="doc.md")
    assert {t.fonte for t in trechos} == {"doc.md"}
    assert [t.ordem for t in trechos] == [0, 1, 2, 3]


def test_secao_sem_corpo_nao_gera_trecho():
    texto = "# D\n\n## Vazia\n\n## Cheia\n\nalgum texto\n"
    assert [t.secao for t in dividir_documento(texto, fonte="d.md")] == ["Cheia"]


def test_documento_vazio_nao_gera_trecho():
    assert dividir_documento("", fonte="d.md") == []
    assert dividir_documento("# Só o título\n", fonte="d.md") == []


# -- código e tabela nunca são partidos ------------------------------------------


def test_cerquilha_dentro_de_codigo_nao_e_titulo():
    texto = (
        "## A\n\n```yaml\n# comentário, não é título\nchave: valor\n```\n\n"
        "## B\n\nfim\n"
    )
    trechos = dividir_documento(texto, fonte="d.md")
    assert [t.secao for t in trechos] == ["A", "B"]
    assert "# comentário, não é título" in trechos[0].conteudo


def test_bloco_de_codigo_gigante_fica_inteiro_num_trecho():
    linhas = "\n".join(f"linha {i} com algumas palavras" for i in range(200))
    codigo = f"```\n{linhas}\n```"
    trechos = dividir_documento(f"## A\n\n{codigo}\n", fonte="d.md", tamanho=40)
    assert len(trechos) == 1
    assert trechos[0].conteudo == codigo


def test_tabela_grande_fica_inteira_com_o_cabecalho():
    linhas = ["|a|b|", "|---|---|"] + [f"|dado {i}|outro dado|" for i in range(80)]
    tabela = "\n".join(linhas)
    trechos = dividir_documento(f"## T\n\n{tabela}\n", fonte="d.md", tamanho=40)
    assert len(trechos) == 1
    assert trechos[0].conteudo.startswith("|a|b|\n|---|---|")
    assert trechos[0].conteudo.endswith("|dado 79|outro dado|")


# -- seção grande é subdividida ----------------------------------------------------


def paragrafo_de_frases(n_frases: int, palavras_por_frase: int = 10) -> str:
    frases = []
    for i in range(n_frases):
        miolo = " ".join(f"p{i}x{j}" for j in range(palavras_por_frase - 1))
        frases.append(f"F{i} {miolo}.")
    return " ".join(frases)


def test_secao_pequena_continua_um_trecho_so():
    texto = "## A\n\num\n\ndois\n\ntrês\n"
    trechos = dividir_documento(texto, fonte="d.md", tamanho=150)
    assert len(trechos) == 1


def test_secao_grande_e_subdividida_e_nenhum_trecho_passa_do_limite():
    texto = f"## A\n\n{paragrafo_de_frases(30)}\n"  # 300 palavras
    trechos = dividir_documento(texto, fonte="d.md", tamanho=60, sobreposicao=0)
    assert len(trechos) > 1
    assert all(t.palavras <= 60 for t in trechos)
    assert {t.secao for t in trechos} == {"A"}


def test_sem_sobreposicao_nenhuma_frase_se_repete():
    texto = f"## A\n\n{paragrafo_de_frases(30)}\n"
    trechos = dividir_documento(texto, fonte="d.md", tamanho=60, sobreposicao=0)
    todas = [f for t in trechos for f in t.conteudo.split(". ")]
    assert len(todas) == len(set(todas))


def test_com_sobreposicao_o_fim_de_um_trecho_abre_o_proximo():
    texto = f"## A\n\n{paragrafo_de_frases(30)}\n"
    # 20% de 50 palavras = 10 palavras = exatamente uma frase de 10 palavras
    trechos = dividir_documento(texto, fonte="d.md", tamanho=50, sobreposicao=20)
    assert len(trechos) > 2
    for anterior, seguinte in pairwise(trechos):
        ultima_frase = anterior.conteudo.split(". ")[-1].rstrip(".")
        assert seguinte.conteudo.startswith(ultima_frase)
    assert all(t.palavras <= 50 for t in trechos)


def test_trechos_vizinhos_de_secoes_diferentes_nao_se_sobrepoem():
    texto = "## A\n\nfrase de a.\n\n## B\n\nfrase de b.\n"
    _, b = dividir_documento(texto, fonte="d.md", sobreposicao=30)
    assert "frase de a" not in b.conteudo


def test_sobreposicao_nao_empurra_o_trecho_para_alem_do_limite():
    """Se a cauda repetida faria o trecho passar do tamanho, ela é descartada."""
    texto = f"## A\n\ncurta introdução.\n\n```\n{'palavra ' * 100}\n```\n"
    trechos = dividir_documento(texto, fonte="d.md", tamanho=60, sobreposicao=30)
    assert "curta introdução." not in trechos[-1].conteudo


# -- o que vai ao modelo de embedding (RF21) ------------------------------------------


def test_texto_para_embedding_comeca_pelo_titulo_da_secao():
    trecho = dividir_documento(DOC, fonte="doc.md")[2]
    assert trecho.texto_para_embedding.startswith("01 Primeira > Sub\n\n")
    assert trecho.texto_para_embedding.endswith("Texto dois.")


def test_trecho_sem_secao_vai_so_com_o_conteudo():
    trecho = dividir_documento(DOC, fonte="doc.md")[0]
    assert trecho.texto_para_embedding == "Texto antes do primeiro título."


# -- a pasta de verdade ----------------------------------------------------------------


def test_dividir_pasta_le_so_os_md_em_ordem_alfabetica(tmp_path):
    (tmp_path / "b.md").write_text("# B\n\n## x\n\ntexto b\n", encoding="utf-8")
    (tmp_path / "a.md").write_text("# A\n\n## x\n\ntexto a\n", encoding="utf-8")
    (tmp_path / "ignorado.txt").write_text("texto solto", encoding="utf-8")
    assert [t.fonte for t in dividir_pasta(tmp_path)] == ["a.md", "b.md"]


@pytest.mark.parametrize("arquivo", ["parte1-cicd-deploy.md", "parte2-rag.md"])
def test_as_apostilas_de_verdade_viram_trechos_razoaveis(arquivo):
    texto = (RAIZ / "documentos" / arquivo).read_text(encoding="utf-8")
    trechos = dividir_documento(texto, fonte=arquivo)
    assert len(trechos) > 30
    assert all(t.conteudo.strip() for t in trechos)
    # só código e tabela podem passar de 150 palavras
    for t in trechos:
        if t.palavras > 150:
            assert t.conteudo.lstrip().startswith(("|", "```")) or "```" in t.conteudo
    assert [t.ordem for t in trechos] == list(range(len(trechos)))


def test_a_divisao_e_deterministica():
    texto = (RAIZ / "documentos" / "parte2-rag.md").read_text(encoding="utf-8")
    assert dividir_documento(texto, fonte="x") == dividir_documento(texto, fonte="x")
