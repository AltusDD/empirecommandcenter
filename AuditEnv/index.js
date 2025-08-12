module.exports = async function (context, req) {
  const pick = (o, keys) => Object.fromEntries(keys.map(k => [k, process.env[k] || null]));
  const expose = ["WEBSITE_SITE_NAME","WEBSITE_INSTANCE_ID","REGION_NAME","WEBSITE_HOSTNAME","AZURE_FUNCTIONS_ENVIRONMENT"];
  const body = { env: pick(process.env, expose), time: new Date().toISOString() };
  context.res = { status: 200, headers: { "Content-Type": "application/json" }, body };
};
