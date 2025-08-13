-- Enable Row Level Security and allow authenticated users to read.
-- This version avoids DO/BEGIN blocks to prevent editor issues.

BEGIN;

-- properties
ALTER TABLE public.properties ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated read access" ON public.properties;
CREATE POLICY "Allow authenticated read access"
ON public.properties
FOR SELECT
TO authenticated
USING (true);

-- units
ALTER TABLE public.units ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated read access" ON public.units;
CREATE POLICY "Allow authenticated read access"
ON public.units
FOR SELECT
TO authenticated
USING (true);

-- leases
ALTER TABLE public.leases ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated read access" ON public.leases;
CREATE POLICY "Allow authenticated read access"
ON public.leases
FOR SELECT
TO authenticated
USING (true);

-- tenants
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow authenticated read access" ON public.tenants;
CREATE POLICY "Allow authenticated read access"
ON public.tenants
FOR SELECT
TO authenticated
USING (true);

COMMIT;
