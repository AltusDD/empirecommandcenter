module.exports = async function (context, req) {
  const lines = [
    "# HELP empire_up 1 if the app is responding",
    "# TYPE empire_up gauge",
    "empire_up 1",
    "# HELP empire_build_info Build info as labels",
    "# TYPE empire_build_info gauge",
    'empire_build_info{app="Empire Command Center"} 1'
  ].join("\n");
  context.res = {
    status: 200,
    headers: { "Content-Type": "text/plain; version=0.0.4" },
    body: lines + "\n"
  };
};
