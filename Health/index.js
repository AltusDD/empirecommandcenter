module.exports = async function (context, req) {
  const now = new Date().toISOString();
  const body = { status: "ok", app: "Empire Command Center", time: now };
  context.res = { status: 200, headers: { "Content-Type": "application/json" }, body };
};
