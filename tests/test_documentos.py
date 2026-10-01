"""Teste da pasta `documentos/` — verificação T17 da spec da parte 2.

Rodam em segundos, sem rede e sem chave. O último teste confere a pasta de verdade:
é o que o CI vai conferir a cada push.
"""

from pathlib import Path

from assistente.conhecimento.documentos import verificar_pasta

RAIZ = Path(__file__).resolve().parent.parent

BOM = "# Título\n\n" + "uma frase com várias palavras de conteúdo real. " * 5


def texto(problemas: list[str]) -> str:
    return " | ".join(problemas)


def test_t17_a_pasta_de_verdade_esta_valida():
    assert verificar_pasta(RAIZ / "documentos") == []


def test_t17_pasta_com_documento_bom_passa(tmp_path):
    (tmp_path / "ok.md").write_text(BOM, encoding="utf-8")
    assert verificar_pasta(tmp_path) == []


def test_t17_pasta_inexistente_e_problema(tmp_path):
    assert "não existe" in texto(verificar_pasta(tmp_path / "nao-ha"))


def test_t17_pasta_vazia_e_problema(tmp_path):
    assert "vazia" in texto(verificar_pasta(tmp_path))


def test_t17_arquivo_que_nao_e_md_e_barrado(tmp_path):
    (tmp_path / "ok.md").write_text(BOM, encoding="utf-8")
    (tmp_path / "apostila.pdf").write_bytes(b"%PDF-1.7 fake")
    (tmp_path / "notas.txt").write_text("solto", encoding="utf-8")
    problemas = texto(verificar_pasta(tmp_path))
    assert "apostila.pdf" in problemas and "notas.txt" in problemas
    assert "ok.md" not in problemas


def test_t17_subpasta_e_barrada(tmp_path):
    (tmp_path / "ok.md").write_text(BOM, encoding="utf-8")
    (tmp_path / "sub").mkdir()
    assert "subpasta" in texto(verificar_pasta(tmp_path))


def test_t17_documento_sem_titulo_e_barrado(tmp_path):
    corpo = "só texto, sem nenhum título. " * 10
    (tmp_path / "sem.md").write_text(corpo, encoding="utf-8")
    assert "não tem título" in texto(verificar_pasta(tmp_path))


def test_t17_titulo_de_nivel_dois_nao_conta_como_titulo_do_documento(tmp_path):
    corpo = "## Só nível dois\n\n" + "palavra " * 40
    (tmp_path / "x.md").write_text(corpo, encoding="utf-8")
    assert "não tem título" in texto(verificar_pasta(tmp_path))


def test_t17_cerquilha_dentro_de_codigo_nao_conta_como_titulo(tmp_path):
    corpo = "```\n# isto é comentário\n```\n" + "palavra " * 40
    (tmp_path / "x.md").write_text(corpo, encoding="utf-8")
    assert "não tem título" in texto(verificar_pasta(tmp_path))


def test_t17_documento_sem_conteudo_e_barrado(tmp_path):
    corpo = "# Título\n\n## Outro título\n"
    (tmp_path / "vazio.md").write_text(corpo, encoding="utf-8")
    assert "quase não tem conteúdo" in texto(verificar_pasta(tmp_path))


def test_t17_arquivo_binario_com_nome_md_e_barrado(tmp_path):
    (tmp_path / "falso.md").write_bytes(b"\xff\xfe\x00\x80\x81")
    assert "UTF-8" in texto(verificar_pasta(tmp_path))


def test_t17_lista_todos_os_problemas_de_uma_vez(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"x")
    (tmp_path / "b.md").write_text("sem título e curto", encoding="utf-8")
    assert len(verificar_pasta(tmp_path)) >= 3
