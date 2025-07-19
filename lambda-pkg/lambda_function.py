from main import generate_ascii_art, gallery
import json

def handler(event, context):
    http = event.get("requestContext", {}).get("http", {})
    path = http.get("path", "").strip("/")
    method = http.get("method")
    headers = event.get("headers", {})
    body = event.get("body", "")

    try:
        body = json.loads(body) if body else {}
    except json.JSONDecodeError:
        pass

    if path == "generate" and method == "POST":
        return generate_ascii_art(headers, http, body)

    elif path == "gallery" and method == "GET":
        return gallery()
