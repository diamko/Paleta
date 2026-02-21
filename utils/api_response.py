from flask import jsonify


def api_success(data=None, status: int = 200, meta=None):
    payload = {"success": True, "data": data if data is not None else {}}
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status


def api_error(code: str, message: str, status: int = 400, details=None):
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), status
