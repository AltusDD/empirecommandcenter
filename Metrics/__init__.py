import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    lines = [
        "# HELP empire_up 1 if the app is responding",
        "# TYPE empire_up gauge",
        "empire_up 1",
        "# HELP empire_build_info Build info as labels",
        "# TYPE empire_build_info gauge",
        'empire_build_info{app="Empire Command Center"} 1'
    ]
    text = "\n".join(lines) + "\n"
    return func.HttpResponse(text, status_code=200, mimetype="text/plain; version=0.0.4")
