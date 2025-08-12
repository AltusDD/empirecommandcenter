-- 01_indexes.sql — FROM GEMINI RECOMMENDATION
CREATE INDEX IF NOT EXISTS leases_active_status_idx
ON public.leases (status, start_date DESC, end_date DESC);

CREATE INDEX IF NOT EXISTS leases_property_id_idx ON public.leases (property_id);
CREATE INDEX IF NOT EXISTS leases_unit_id_idx ON public.leases (unit_id);
