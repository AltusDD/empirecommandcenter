-- verify_all_v2.sql — schema-safe audit for ALL DoorLoop entities
-- Copy/paste into Supabase SQL Editor and Run.

-- A) Raw vs Normalized counts
with counts as (
  select 'properties'::text as entity, (select count(*) from doorloop_raw_properties) as raw_rows, (select count(*) from properties) as normalized_rows union all
  select 'units',            (select count(*) from doorloop_raw_units),            (select count(*) from units) union all
  select 'leases',           (select count(*) from doorloop_raw_leases),           (select count(*) from leases) union all
  select 'tenants',          (select count(*) from doorloop_raw_tenants),          (select count(*) from tenants) union all
  select 'owners',           (select count(*) from doorloop_raw_owners),           (select count(*) from owners) union all
  select 'lease_payments',   (select count(*) from doorloop_raw_lease_payments),   (select count(*) from lease_payments) union all
  select 'lease_charges',    (select count(*) from doorloop_raw_lease_charges),    (select count(*) from lease_charges) union all
  select 'lease_credits',    (select count(*) from doorloop_raw_lease_credits),    (select count(*) from lease_credits) union all
  select 'vendors',          (select count(*) from doorloop_raw_vendors),          (select count(*) from vendors) union all
  select 'tasks',            (select count(*) from doorloop_raw_tasks),            (select count(*) from tasks) union all
  select 'notes',            (select count(*) from doorloop_raw_notes),            (select count(*) from notes) union all
  select 'files',            (select count(*) from doorloop_raw_files),            (select count(*) from files) union all
  select 'communications',   (select count(*) from doorloop_raw_communications),   (select count(*) from communications)
)
select entity, raw_rows, normalized_rows,
       case when raw_rows=0 then 0 when normalized_rows=0 then 0 else round(100.0*normalized_rows/raw_rows,1) end as parity_pct
from counts order by 1;

-- B) FK integrity (schema-aware). Prints SKIPPED if a column/table is missing.
with cols as (
  select table_name, column_name
  from information_schema.columns
  where table_schema='public'
),
checks as (
  select 'leases_missing_property_fk'::text as check_name, case
    when exists (select 1 from cols where table_name='leases' and column_name='property_id')
    then (select count(*) from leases where property_id is null)
    else -1 end as n
  union all
  select 'leases_missing_unit_fk', case
    when exists (select 1 from cols where table_name='leases' and column_name='unit_id')
    then (select count(*) from leases where unit_id is null)
    else -1 end
  union all
  select 'leases_missing_tenant_fk', case
    when exists (select 1 from cols where table_name='leases' and column_name='tenant_id')
    then (select count(*) from leases where tenant_id is null)
    else -1 end
  union all
  select 'payments_missing_lease_fk', case
    when exists (select 1 from cols where table_name='lease_payments' and column_name='lease_id')
    then (select count(*) from lease_payments where lease_id is null)
    else -1 end
  union all
  select 'charges_missing_lease_fk', case
    when exists (select 1 from cols where table_name='lease_charges' and column_name='lease_id')
    then (select count(*) from lease_charges where lease_id is null)
    else -1 end
  union all
  select 'credits_missing_lease_fk', case
    when exists (select 1 from cols where table_name='lease_credits' and column_name='lease_id')
    then (select count(*) from lease_credits where lease_id is null)
    else -1 end
)
select check_name,
  case when n = -1 then 'SKIPPED – column not found' else n::text end as result_text
from checks;

-- C) KPI freshness (if the KPI table exists)
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='kpi_summary') then
    perform 1;
    execute 'select * from kpi_summary order by calculated_at desc limit 1';
  else
    raise notice 'kpi_summary table not found (skipping)';
  end if;
end$$;

-- D) Properties ZIP completeness (schema-aware)
do $$
begin
  if exists (select 1 from information_schema.columns where table_schema='public' and table_name='properties' and column_name='zip') then
    execute $q$
      select
        sum((zip is null or zip='')::int) as zip_missing,
        count(*) as total
      from properties;
    $q$;
  elsif exists (select 1 from information_schema.columns where table_schema='public' and table_name='properties' and column_name='address_zip') then
    execute $q$
      select
        sum((address_zip is null or address_zip='')::int) as zip_missing,
        count(*) as total
      from properties;
    $q$;
  else
    raise notice 'No ZIP column on properties (zip/address_zip not found)';
  end if;
end$$;

-- E) Units status distribution (if status exists)
do $$
begin
  if exists (select 1 from information_schema.columns where table_schema='public' and table_name='units' and column_name='status') then
    execute 'select lower(coalesce(status,'''')) as status, count(*) from units group by 1 order by 2 desc';
  else
    raise notice 'units.status column not found (skipping status histogram)';
  end if;
end$$;
