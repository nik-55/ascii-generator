from main import generate_ascii_art, gallery


def handler(event, context):
    path = event.get("path", "").strip("/")

    if path == "generate":
        return generate_ascii_art(event, context)

    elif path == "gallery":
        return gallery(event, context)
