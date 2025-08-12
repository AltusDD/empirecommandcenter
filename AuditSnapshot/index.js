module.exports = async function (context, req) {
  // Placeholder snapshot; replace with real counts when ready
  const now = new Date().toISOString();
  const body = {
    generated_at: now,
    totals: { properties: 0, units: 0, leases: 0, tenants: 0 },
    kpis: { occupancy_pct: null, churn_30d: null },
    source: "placeholder"
  };
  context.res = { status: 200, headers: { "Content-Type": "application/json" }, body };
};
