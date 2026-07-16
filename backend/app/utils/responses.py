from flask import jsonify


def success_response(data=None, message="ok", status_code=200):
    payload = {
        "success": True,
        "data": data or {},
        "message": message,
    }
    return jsonify(payload), status_code


def error_response(code, message, details=None, status_code=400):
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }
    return jsonify(payload), status_code
