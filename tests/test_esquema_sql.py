"""Guarda as linhas de permissão do `supabase/esquema.sql` (RF34 e RF35).

O SQL é rodado à mão no Supabase, então não dá para executá-lo no CI. Mas dá para
garantir, lendo o arquivo, que ninguém afrouxou por engano uma permissão que
protege o índice: quem tem o quê, em cada função, está escrito aqui.
"""

import re
from pathlib import Path

import pytest

SQL = (Path(__file__).resolve().parent.parent / "supabase" / "esquema.sql").read_text(
    encoding="utf-8"
)
SEM_COMENTARIOS = re.sub(r"--[^\n]*", "", SQL)

# função -> quem pode executar (anon = a chave publicável, service_role = a secreta)
QUEM_PODE = {
    "busca_interna": {"service_role"},
    "buscar_producao": {"anon", "authenticated", "service_role"},
    "buscar_teste": {"service_role"},
    "promover": {"service_role"},
    "contar_producao": {"anon", "authenticated", "service_role"},
}


def concedidos(funcao: str) -> set[str]:
    achados = re.findall(
        rf"grant\s+execute\s+on\s+function\s+public\.{funcao}\([^)]*\)\s+to\s+([^;]+);",
        SEM_COMENTARIOS,
    )
    assert achados, f"nenhum grant para {funcao}"
    return {quem.strip() for trecho in achados for quem in trecho.split(",")}


@pytest.mark.parametrize(("funcao", "esperado"), QUEM_PODE.items())
def test_cada_funcao_e_concedida_so_a_quem_deve(funcao, esperado):
    assert concedidos(funcao) == esperado


@pytest.mark.parametrize("funcao", QUEM_PODE)
def test_cada_funcao_tem_o_execute_revogado_de_todos_antes_do_grant(funcao):
    padrao = (
        rf"revoke\s+all\s+on\s+function\s+public\.{funcao}\([^)]*\)\s+"
        r"from\s+public,\s*anon,\s*authenticated\s*;"
    )
    assert re.search(padrao, SEM_COMENTARIOS), f"{funcao}: falta o revoke de todos"


def test_a_tabela_tem_rls_ligado_e_nenhum_privilegio_para_a_chave_publicavel():
    assert re.search(
        r"alter\s+table\s+public\.trechos\s+enable\s+row\s+level\s+security",
        SEM_COMENTARIOS,
    )
    assert re.search(
        r"revoke\s+all\s+on\s+public\.trechos\s+from\s+public,\s*anon,\s*authenticated",
        SEM_COMENTARIOS,
    )
    assert not re.search(
        r"grant\s+[^;]*on\s+(table\s+)?public\.trechos", SEM_COMENTARIOS
    )


def test_nenhuma_politica_de_leitura_abre_a_tabela():
    assert "create policy" not in SEM_COMENTARIOS.lower()


def test_toda_funcao_roda_com_security_definer_e_search_path_fixo():
    funcoes = re.split(r"create\s+or\s+replace\s+function", SEM_COMENTARIOS)[1:]
    assert len(funcoes) == len(QUEM_PODE)
    for corpo in funcoes:
        cabecalho = corpo.split("$$")[0].lower()
        assert "security definer" in cabecalho
        assert re.search(r"set\s+search_path\s*=", cabecalho)


def test_vetor_tem_384_dimensoes_como_o_modelo_de_embedding():
    assert re.search(r"embedding\s+vector\(384\)\s+not\s+null", SEM_COMENTARIOS)


def test_colecao_so_aceita_teste_ou_producao():
    assert "check (colecao in ('teste', 'producao'))" in SEM_COMENTARIOS


def test_promover_recusa_versao_que_nao_confere():
    assert "nada foi promovido" in SEM_COMENTARIOS
    assert "update public.trechos set colecao = 'producao' where colecao = 'teste'" in (
        SEM_COMENTARIOS
    )
