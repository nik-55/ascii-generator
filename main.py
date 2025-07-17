import datetime
import json
import uuid
import base64
import requests
import os

from jinja2 import Environment, FileSystemLoader
from fastapi.responses import Response
from pydantic_settings import BaseSettings, SettingsConfigDict

from prompt import modify_system_prompt
from rate import S3Uploader, s3_base_url, session, is_rate_limited
from utils import ascii_generator


class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


settings = Settings()
env = Environment(loader=FileSystemLoader("templates"))


# "/gallery"
def gallery(
    event,
    context,
):
    s3 = session.client("s3", region_name="ap-south-1")
    response = s3.list_objects_v2(Bucket="ascii-generator-123", Prefix="gallery-view/")

    all_keys = [
        obj["Key"].replace("/data.json", "")
        for obj in response.get("Contents", [])
        if obj["Key"].endswith("data.json")
    ]

    data = []
    for key in all_keys:
        res = s3.get_object(Bucket="ascii-generator-123", Key=f"{key}/data.json")
        data_json = json.loads(res["Body"].read().decode("utf-8"))
        prompt = data_json["prompt"]

        key = f"{s3_base_url}/{key}"

        data.append(
            {
                "prompt": prompt,
                "original_img_path": f"{key}/img.png",
                "art_html_path": f"{key}/art-show.html",
                "ascii_art_path": f"{key}/ascii_art.txt",
                "art_iframe_html_path": f"{key}/art-iframe.html",
            }
        )

    return data


# /generate/
def generate_ascii_art(
    event,
    context,
):
    x_forwarded_for = event.get("headers", {}).get("X-Forwarded-For")
    ip = (
        x_forwarded_for.split(",")[0].strip()
        if x_forwarded_for
        else event.get("requestContext", {}).get("identity", {}).get("sourceIp")
    )

    if is_rate_limited(ip):
        return Response(
            "You have exceeded rate limit ;-; Please try again later.",
            status_code=429,
        )

    prompt = json.loads(event.get("body", {})).get("prompt", "").strip()

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

    art, clr_array, clr_str = ascii_generator(f"/tmp/img.png")
    art_arr = [list(line) for line in art.split("\n")]

    context = {
        "art": art_arr,
        "clr_arr": clr_array,
        "prompt": prompt,
        "ascii_art_path": f"/gallery-view/{day_of_month}/{img_id}/ascii_art.txt",
    }

    html_str = env.get_template("art.html").render(context)

    s3_uploader.upload_file(
        content=html_str.encode("utf-8"),
        s3_key=f"gallery-view/{day_of_month}/{img_id}/art-show.html",
        extra_args={"ContentType": "text/html"},
    )

    html_str = html_str.replace("await new Promise(res => setTimeout(res, delay));", "")

    s3_uploader.upload_file(
        content=html_str.encode("utf-8"),
        s3_key=f"gallery-view/{day_of_month}/{img_id}/art.html",
        extra_args={"ContentType": "text/html"},
    )

    s3_uploader.upload_file(
        content=clr_str.encode("utf-8"),
        s3_key=f"gallery-view/{day_of_month}/{img_id}/ascii_art.txt",
        extra_args={"ContentType": "text/plain"},
    )

    iframe_html_str = env.get_template("art-iframe.html").render(context)

    s3_uploader.upload_file(
        content=iframe_html_str.encode("utf-8"),
        s3_key=f"gallery-view/{day_of_month}/{img_id}/art-iframe.html",
        extra_args={"ContentType": "text/html"},
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "url": f"{s3_base_url}/gallery-view/{day_of_month}/{img_id}/art-show.html",
            }
        ),
    }
