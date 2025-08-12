-- Run once in Supabase SQL Editor
create or replace function public.export_schema_manifest(schema_name text default 'public')
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  with tables as (
    select c.oid as table_oid, t.table_name,
           jsonb_agg(jsonb_build_object(
             'name', col.column_name,
             'data_type', col.data_type,
             'udt_name', col.udt_name,
             'is_nullable', col.is_nullable,
             'column_default', col.column_default,
             'identity', col.is_identity
           ) order by col.ordinal_position) as columns
    from information_schema.tables t
    join information_schema.columns col
      on col.table_schema = t.table_schema and col.table_name = t.table_name
    join pg_class c on c.relname = t.table_name
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = t.table_schema
    where t.table_schema = schema_name and t.table_type = 'BASE TABLE'
    group by c.oid, t.table_name
  ),
  pks as (
    select c.conrelid as table_oid,
           jsonb_agg(att.attname order by s.i) as pk_columns
    from (select c.conrelid, c.conkey, generate_subscripts(c.conkey,1) as i
          from pg_constraint c join pg_namespace n on n.oid = c.connamespace
          where c.contype='p' and n.nspname=schema_name) s
    join pg_attribute att on att.attrelid=s.conrelid and att.attnum=s.conkey[s.i]
    join pg_constraint c on c.conrelid=s.conrelid
    group by c.conrelid
  ),
  fks as (
    select c.conrelid as table_oid,
           jsonb_agg(jsonb_build_object(
             'constraint_name', c.conname,
             'columns', fk_cols.cols,
             'ref_schema', ref_n.nspname,
             'ref_table', ref_cl.relname,
             'ref_columns', ref_cols.cols,
             'on_update', c.confupdtype::text,
             'on_delete', c.confdeltype::text
           )) as foreign_keys
    from pg_constraint c
    join pg_class cl on cl.oid=c.conrelid
    join pg_namespace n on n.oid=cl.relnamespace
    join pg_class ref_cl on ref_cl.oid=c.confrelid
    join pg_namespace ref_n on ref_n.oid=ref_cl.relnamespace
    left join lateral (
      select jsonb_agg(att.attname order by i) as cols
      from (select generate_subscripts(c.conkey,1) i) x
      join pg_attribute att on att.attrelid=c.conrelid and att.attnum=c.conkey[x.i]
    ) fk_cols on true
    left join lateral (
      select jsonb_agg(att.attname order by i) as cols
      from (select generate_subscripts(c.confkey,1) i) x
      join pg_attribute att on att.attrelid=c.confrelid and att.attnum=c.confkey[x.i]
    ) ref_cols on true
    where c.contype='f' and n.nspname=schema_name
    group by c.conrelid
  ),
  idx as (
    select t.oid as table_oid,
           jsonb_agg(jsonb_build_object('name', i.indexname, 'definition', i.indexdef) order by i.indexname) as indexes
    from pg_class t
    join pg_namespace n on n.oid=t.relnamespace
    join pg_indexes i on i.tablename=t.relname and i.schemaname=n.nspname
    where n.nspname=schema_name and t.relkind='r'
    group by t.oid
  ),
  tables_full as (
    select tables.table_name, tables.columns,
           coalesce(pks.pk_columns,'[]'::jsonb) as primary_key,
           coalesce(fks.foreign_keys,'[]'::jsonb) as foreign_keys,
           coalesce(idx.indexes,'[]'::jsonb) as indexes
    from tables
    left join pks on pks.table_oid=tables.table_oid
    left join fks on fks.table_oid=tables.table_oid
    left join idx on idx.table_oid=tables.table_oid
  ),
  views as (
    select c.relname as view_name,
           case when c.relkind='m' then 'MATERIALIZED' else 'VIEW' end as kind,
           pg_get_viewdef(c.oid, true) as definition
    from pg_class c
    join pg_namespace n on n.oid=c.relnamespace
    where n.nspname=schema_name and c.relkind in ('v','m')
  ),
  funcs as (
    select n.nspname as schema, p.proname as name,
           pg_get_function_identity_arguments(p.oid) as args,
           pg_get_function_result(p.oid) as returns,
           pg_get_functiondef(p.oid) as definition
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname=schema_name
  ),
  trigs as (
    select t.tgname as trigger_name, c.relname as table_name,
           pg_get_triggerdef(t.oid, true) as definition
    from pg_trigger t join pg_class c on c.oid=t.tgrelid
    join pg_namespace n on n.oid=c.relnamespace
    where n.nspname=schema_name and not t.tgisinternal
  ),
  enums as (
    select t.typname as enum_name,
           jsonb_agg(e.enumlabel order by e.enumsortorder) as labels
    from pg_type t join pg_enum e on e.enumtypid=t.oid
    join pg_namespace n on n.oid=t.typnamespace
    where n.nspname=schema_name
    group by t.typname
  ),
  sequences as (
    select sequence_name, data_type, start_value, minimum_value, maximum_value, increment, cycle_option
    from information_schema.sequences
    where sequence_schema=schema_name
  ),
  ext as (select extname from pg_extension)
  select jsonb_build_object(
    'generated_at', now(),
    'schema', schema_name,
    'tables', coalesce((select jsonb_agg(to_jsonb(tables_full) order by tables_full.table_name) from tables_full),'[]'::jsonb),
    'views', coalesce((select jsonb_agg(jsonb_build_object('view_name',view_name,'kind',kind,'definition',definition) order by view_name) from views),'[]'::jsonb),
    'functions', coalesce((select jsonb_agg(to_jsonb(funcs) order by name) from funcs),'[]'::jsonb),
    'triggers', coalesce((select jsonb_agg(to_jsonb(trigs) order by trigger_name) from trigs),'[]'::jsonb),
    'enums', coalesce((select jsonb_agg(to_jsonb(enums) order by enum_name) from enums),'[]'::jsonb),
    'sequences', coalesce((select jsonb_agg(to_jsonb(sequences) order by sequence_name) from sequences),'[]'::jsonb),
    'extensions', coalesce((select jsonb_agg(extname) from ext),'[]'::jsonb)
  );
$$;

grant execute on function public.export_schema_manifest(text) to anon, authenticated, service_role;
