import os, json, azure.functions as func
import dropbox

def main(req: func.HttpRequest) -> func.HttpResponse:
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    refresh = os.getenv("DROPBOX_REFRESH_TOKEN")
    body = {"env": {"has_app_key": bool(app_key), "has_app_secret": bool(app_secret), "has_refresh": bool(refresh)}}

    if not all([app_key, app_secret, refresh]):
        body["ok"] = False
        body["reason"] = "Missing one or more of DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN"
        return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")

    try:
        dbx = dropbox.Dropbox(oauth2_refresh_token=refresh, app_key=app_key, app_secret=app_secret, timeout=30)
        acct = dbx.users_get_current_account()
        space = dbx.users_get_space_usage()
        body.update({
            "ok": True,
            "account": {"name": acct.name.display_name, "email": getattr(acct, "email", None)},
            "space": {"used": space.used, "allocation": getattr(space.allocation, "allocated", None)},
        })
        # List root folder
        try:
            res = dbx.files_list_folder("", limit=10)
            items = [{"name": e.name, "path_lower": e.path_lower, "type": type(e).__name__} for e in res.entries]
            body["root_list"] = items
        except Exception as e:
            body["root_list_error"] = str(e)
        return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")
    except Exception as e:
        body["ok"] = False
        body["error"] = str(e)
        return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")
