-- =============================================================================
--  Esquema do banco da base de consulta (parte 2)
--
--  Como usar: abra o Supabase, SQL Editor, cole TUDO e clique em Run.
--  Pode rodar de novo sem medo: cada comando é "criar se não existir" ou
--  "substituir". (Se um dia mudar as COLUNAS da tabela, apague a tabela antes.)
--
--  O que isto cria:
--    1. A tabela `trechos`: cada linha é um pedaço de documento com o seu vetor.
--    2. A busca híbrida (palavras + sentido, fundidas por RRF).
--    3. As funções que o app e o pipeline chamam.
--    4. As PERMISSÕES, que são o que impede a chave que está no Space de
--       ler ou apagar o que não deve.
--
--  Dois conjuntos de trechos convivem na mesma tabela, separados pela coluna
--  `colecao`:   teste     o índice novo, em avaliação (só o pipeline enxerga)
--               producao  o índice que o assistente no ar consulta
-- =============================================================================

create extension if not exists vector with schema extensions;


-- 1. A tabela ------------------------------------------------------------------

create table if not exists public.trechos (
  id         bigint generated always as identity primary key,
  colecao    text    not null check (colecao in ('teste', 'producao')),
  versao     text    not null,              -- hash do commit que gerou a linha
  fonte      text    not null,              -- arquivo de origem, ex.: parte2-rag.md
  secao      text    not null default '',   -- título da seção, com o caminho acima
  ordem      integer not null,              -- posição do trecho no documento
  conteudo   text    not null,
  embedding  vector(384) not null,          -- paraphrase-multilingual-MiniLM-L12-v2
  -- índice da busca por palavras, mantido pelo próprio banco, em português
  palavras   tsvector generated always as (
               to_tsvector('portuguese', coalesce(secao, '') || ' ' || conteudo)
             ) stored
);

create index if not exists trechos_palavras_gin on public.trechos using gin (palavras);
create unique index if not exists trechos_unico
  on public.trechos (colecao, fonte, ordem);


-- 2. Permissões da tabela --------------------------------------------------------
-- Ninguém além do dono e da chave SECRETA toca na tabela diretamente. Com RLS
-- ligado e nenhuma política, e sem nenhum privilégio concedido, a chave publicável
-- não lê, não grava e não apaga nada. Ela só consegue chamar as funções do item 4.

alter table public.trechos enable row level security;
revoke all on public.trechos from public, anon, authenticated;


-- 3. A busca híbrida ---------------------------------------------------------------
-- Duas listas (as 20 melhores de cada), fundidas por RRF: 1 / (60 + posição),
-- multiplicado pelo peso de cada tipo de busca. Peso zero desliga aquela busca.
--
--  * Por palavras: a busca textual do Postgres, em português ("guardo" e
--    "guardar" viram a mesma raiz). Uma pergunta em linguagem natural quase nunca
--    tem TODAS as palavras do trecho, então as palavras entram com OU, não E.
--  * Por sentido: a distância do cosseno do pgvector (<=>), busca exata.
--  * Um trecho que só apareceu pelo sentido, com similaridade abaixo de
--    `p_sim_min`, é descartado. Trecho achado pelas palavras sempre fica.
--
-- Esta função é de uso interno: ninguém a chama de fora (veja as permissões).

create or replace function public.busca_interna(
  p_colecao       text,
  p_pergunta      text,
  p_vetor         vector,
  p_n             integer,
  p_peso_palavras real,
  p_peso_sentido  real,
  p_sim_min       real
)
returns table (
  id bigint, fonte text, secao text, ordem integer, conteudo text,
  nota real, similaridade real
)
language sql
stable
security definer
set search_path = public, extensions
as $$
  with consulta as (
    select nullif(
             replace(plainto_tsquery('portuguese', p_pergunta)::text, ' & ', ' | '),
             ''
           )::tsquery as q
  ),
  por_palavras as (
    select t.id,
           row_number() over (order by ts_rank_cd(t.palavras, c.q) desc, t.id) as pos
    from public.trechos t, consulta c
    where p_peso_palavras > 0
      and c.q is not null
      and t.colecao = p_colecao
      and t.palavras @@ c.q
    order by ts_rank_cd(t.palavras, c.q) desc, t.id
    limit 20
  ),
  por_sentido as (
    select t.id,
           row_number() over (order by t.embedding <=> p_vetor, t.id) as pos,
           1 - (t.embedding <=> p_vetor) as sim
    from public.trechos t
    where p_peso_sentido > 0
      and t.colecao = p_colecao
    order by t.embedding <=> p_vetor, t.id
    limit 20
  ),
  fusao as (
    select coalesce(p.id, s.id) as id,
           coalesce(p_peso_palavras / (60.0 + p.pos), 0)
         + coalesce(p_peso_sentido  / (60.0 + s.pos), 0) as nota
    from por_palavras p
    full join por_sentido s on s.id = p.id
    where p.id is not null or s.sim >= p_sim_min
  )
  select t.id, t.fonte, t.secao, t.ordem, t.conteudo,
         f.nota::real,
         (1 - (t.embedding <=> p_vetor))::real
  from fusao f
  join public.trechos t on t.id = f.id
  order by f.nota desc, t.id
  limit p_n;
$$;


-- 4. As funções públicas ---------------------------------------------------------------

-- O app, no Space, chama esta: só enxerga a coleção `producao`.
create or replace function public.buscar_producao(
  p_pergunta      text,
  p_vetor         vector,
  p_n             integer default 4,
  p_peso_palavras real    default 1,
  p_peso_sentido  real    default 1,
  p_sim_min       real    default 0.30
)
returns table (
  id bigint, fonte text, secao text, ordem integer, conteudo text,
  nota real, similaridade real
)
language sql
stable
security definer
set search_path = public, extensions
as $$
  select * from public.busca_interna(
    'producao', p_pergunta, p_vetor, p_n, p_peso_palavras, p_peso_sentido, p_sim_min
  );
$$;

-- O job `avaliar` chama esta: a mesma busca, na coleção `teste`.
create or replace function public.buscar_teste(
  p_pergunta      text,
  p_vetor         vector,
  p_n             integer default 4,
  p_peso_palavras real    default 1,
  p_peso_sentido  real    default 1,
  p_sim_min       real    default 0.30
)
returns table (
  id bigint, fonte text, secao text, ordem integer, conteudo text,
  nota real, similaridade real
)
language sql
stable
security definer
set search_path = public, extensions
as $$
  select * from public.busca_interna(
    'teste', p_pergunta, p_vetor, p_n, p_peso_palavras, p_peso_sentido, p_sim_min
  );
$$;

-- O job `publicar` chama esta: troca o índice no ar pelo que foi avaliado, de uma
-- vez (uma função é uma transação só: quem consulta vê o índice antigo inteiro
-- ou o novo inteiro, nunca metade de cada). Só promove se a coleção `teste` for
-- exatamente a do commit que está sendo publicado.
create or replace function public.promover(p_versao text)
returns integer
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  n integer;
begin
  select count(*) into n
  from public.trechos where colecao = 'teste' and versao = p_versao;

  if n = 0 then
    raise exception 'a colecao teste nao tem a versao % — nada foi promovido', p_versao;
  end if;
  if exists (select 1 from public.trechos where colecao = 'teste' and versao <> p_versao) then
    raise exception 'a colecao teste mistura versoes — nada foi promovido';
  end if;

  delete from public.trechos where colecao = 'producao';
  update public.trechos set colecao = 'producao' where colecao = 'teste';
  return n;
end;
$$;

-- O app chama esta no início, para escrever no log "N trechos na produção".
create or replace function public.contar_producao()
returns integer
language sql
stable
security definer
set search_path = public
as $$
  select count(*)::integer from public.trechos where colecao = 'producao';
$$;


-- 5. Quem pode chamar o quê (o "menor privilégio" de verdade) --------------------------
-- Por padrão, o Postgres e o Supabase deixam QUALQUER um executar uma função nova.
-- Aqui se tira de todo mundo e se devolve só a quem precisa.
--   anon / authenticated  = a chave PUBLICÁVEL (a do Space)
--   service_role          = a chave SECRETA (a do GitHub Actions)

revoke all on function public.busca_interna(text, text, vector, integer, real, real, real)
  from public, anon, authenticated;
grant execute on function public.busca_interna(text, text, vector, integer, real, real, real)
  to service_role;

revoke all on function public.buscar_producao(text, vector, integer, real, real, real)
  from public, anon, authenticated;
grant execute on function public.buscar_producao(text, vector, integer, real, real, real)
  to anon, authenticated, service_role;

revoke all on function public.buscar_teste(text, vector, integer, real, real, real)
  from public, anon, authenticated;
grant execute on function public.buscar_teste(text, vector, integer, real, real, real)
  to service_role;

revoke all on function public.promover(text) from public, anon, authenticated;
grant execute on function public.promover(text) to service_role;

revoke all on function public.contar_producao() from public, anon, authenticated;
grant execute on function public.contar_producao() to anon, authenticated, service_role;

-- Avisa a API do Supabase que as funções mudaram (sem isto, ela pode demorar a ver).
notify pgrst, 'reload schema';


-- 6. Para conferir (rode à parte, depois) ----------------------------------------------
--   select count(*) from public.trechos;                -- 0: a tabela está vazia
--   select public.contar_producao();                    -- 0
--   select proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--    where n.nspname = 'public' and proname in
--      ('busca_interna','buscar_producao','buscar_teste','promover','contar_producao');
--                                                        -- 5 linhas
