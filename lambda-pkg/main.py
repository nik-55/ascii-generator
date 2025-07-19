import datetime
import json
import uuid
import base64
import requests
import os

from jinja2 import Environment, FileSystemLoader

from prompt import modify_system_prompt
from rate import S3Uploader, s3_base_url, session, is_rate_limited
from utils import ascii_generator


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


settings = Settings()
env = Environment(loader=FileSystemLoader("templates"))


def gallery():
    s3 = session.client("s3", region_name="ap-south-1")
    response = s3.list_objects_v2(Bucket="ascii-generator-123", Prefix="gallery-view/")

    keys = [
        obj["Key"].replace("gallery-view/", "").replace("/data.json", "")
        for obj in response.get("Contents", [])
        if obj["Key"].endswith("data.json")
    ]

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=200",
        },
        "body": json.dumps(
            {
                "keys": keys,
            }
        ),
    }


def generate_ascii_art(
    headers,
    http,
    body,
):
    x_forwarded_for = headers.get("X-Forwarded-For")
    ip = (
        x_forwarded_for.split(",")[0].strip()
        if x_forwarded_for
        else http.get("sourceIp")
    )

    if is_rate_limited(ip):
        return {
            "statusCode": 429,
            "headers": {"Content-Type": "text/plain"},
            "body": "You have exceeded rate limit ;-; Please try again later.",
        }

    prompt = body.get("prompt", "").strip()

    if not prompt:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "text/plain"},
            "body": "Prompt cannot be empty",
        }

    headers = {
        "x-goog-api-key": settings.GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    res_modified_prompt = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers=headers,
        json={
            "contents": [{"parts": [{"text": f"{modify_system_prompt}\n\n{prompt}"}]}],
        },
    )

    if res_modified_prompt.status_code != 200:
        print(res_modified_prompt.text, flush=True)
        return "Error occured ;-;"

    modified_prompt = res_modified_prompt.json()["candidates"][0]["content"]["parts"][
        0
    ]["text"]

    res = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent",
        headers=headers,
        json={
            "contents": [{"parts": [{"text": modified_prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        },
    )

    img_id = str(uuid.uuid4())[:7]
    day_of_month = datetime.datetime.now().day

    s3_uploader = S3Uploader()
    s3_uploader.upload_file(
        content=json.dumps(
            {
                "prompt": prompt,
                "modified_prompt": modified_prompt,
            }
        ).encode("utf-8"),
        s3_key=f"gallery-view/{day_of_month}/{img_id}/data.json",
        extra_args={"ContentType": "application/json"},
    )

    data = res.json()

    try:
        base64_str = data["candidates"][0]["content"]["parts"][1]["inlineData"]["data"]
    except Exception as e:
        print(e, flush=True)
        return "Error occured ;-;"

    s3_uploader.upload_file(
        content=base64.b64decode(base64_str),
        s3_key=f"gallery-view/{day_of_month}/{img_id}/img.png",
        extra_args={"ContentType": "image/png"},
    )

    with open(f"/tmp/img.png", "wb") as f:
        f.write(base64.b64decode(base64_str))

    gray_str, colored_array, colored_str = ascii_generator(f"/tmp/img.png")
    gray_array = [list(line) for line in gray_str.split("\n")]

    context = {
        "gray_array": gray_array,
        "colored_array": colored_array,
        "prompt": prompt,
        "id": f"{day_of_month}/{img_id}",
    }

    s3_uploader.upload_file(
        content=colored_str.encode("utf-8"),
        s3_key=f"gallery-view/{day_of_month}/{img_id}/art-colored.txt",
        extra_args={
            "ContentType": "text/plain",
            "CacheControl": "public, max-age=31536000, immutable",
        },
    )

    s3_uploader.upload_file(
        content=gray_str.encode("utf-8"),
        s3_key=f"gallery-view/{day_of_month}/{img_id}/art-gray.txt",
        extra_args={
            "ContentType": "text/plain",
            "CacheControl": "public, max-age=31536000, immutable",
        },
    )

    s3_uploader.upload_file(
        content=json.dumps(context).encode("utf-8"),
        s3_key=f"gallery-view/{day_of_month}/{img_id}/context.json",
        extra_args={
            "ContentType": "application/json",
            "CacheControl": "public, max-age=31536000, immutable",
        },
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "id": f"{day_of_month}/{img_id}",
            }
        ),
    }
