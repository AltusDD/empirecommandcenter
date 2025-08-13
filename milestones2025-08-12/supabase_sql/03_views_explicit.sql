-- 03_views_explicit.sql — example explicit views (run after team sign-off)
-- Adjust column names if they differ in your DB.

CREATE OR REPLACE VIEW public.active_leases_v AS
SELECT
  l.id          AS lease_id,
  l.property_id AS property_id,
  l.unit_id     AS unit_id,
  l.start_date,
  l.end_date,
  l.status
FROM public.leases l
WHERE l.status IN ('ACTIVE','RENEWAL','HOLDOVER','MONTH_TO_MONTH')
  AND l.start_date <= CURRENT_DATE
  AND (l.end_date IS NULL OR l.end_date >= CURRENT_DATE);

CREATE OR REPLACE VIEW public.leases_enriched_v AS
SELECT
  l.id          AS lease_id,
  l.status      AS lease_status,
  l.start_date,
  l.end_date,
  p.id          AS property_id,
  p.name        AS property_name,
  u.id          AS unit_id,
  COALESCE(u.name, u.unit_number::text) AS unit_name
FROM public.leases l
JOIN public.properties p ON p.id = l.property_id
JOIN public.units u ON u.id = l.unit_id;

CREATE OR REPLACE VIEW public.property_occupancy_v AS
SELECT
  p.id   AS property_id,
  p.name AS property_name,
  (SELECT COUNT(*) FROM public.units u WHERE u.property_id = p.id) AS total_units,
  (SELECT COUNT(DISTINCT al.unit_id) FROM public.active_leases_v al WHERE al.property_id = p.id) AS occupied_units,
  CASE WHEN (SELECT COUNT(*) FROM public.units u WHERE u.property_id = p.id) = 0
       THEN 0
       ELSE ROUND( ( (SELECT COUNT(DISTINCT al.unit_id) FROM public.active_leases_v al WHERE al.property_id = p.id)::numeric
                     / NULLIF((SELECT COUNT(*) FROM public.units u WHERE u.property_id = p.id),0)::numeric ) * 100, 1)
  END AS occupancy_pct
FROM public.properties p;
