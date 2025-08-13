-- 02_rls_enable.sql — enable RLS and allow authenticated reads
ALTER TABLE public.properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.units ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.leases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE polname='Allow authenticated read access' AND tablename='properties') THEN
    CREATE POLICY "Allow authenticated read access" ON public.properties FOR SELECT TO authenticated USING (true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE polname='Allow authenticated read access' AND tablename='units') THEN
    CREATE POLICY "Allow authenticated read access" ON public.units FOR SELECT TO authenticated USING (true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE polname='Allow authenticated read access' AND tablename='leases') THEN
    CREATE POLICY "Allow authenticated read access" ON public.leases FOR SELECT TO authenticated USING (true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE polname='Allow authenticated read access' AND tablename='tenants') THEN
    CREATE POLICY "Allow authenticated read access" ON public.tenants FOR SELECT TO authenticated USING (true);
  END IF;
END $$;
