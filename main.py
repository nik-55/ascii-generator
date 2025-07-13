import datetime
import json
import requests

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from prompt import modify_system_prompt
from fastapi.responses import Response
from cache import cache


class Settings(BaseSettings):
    GEMINI_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra=None)


settings = Settings()
app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/hello")
async def hello(request: Request):
    return "Ok"


@app.get("/gallery")
@cache(seconds=200)
async def gallery(request: Request):
    import os

    dir_path = f"./media"

    data = []
    dirs = os.listdir(dir_path)

    for day_dir in dirs:
        if not day_dir.isdigit():
            continue

        day_path = os.path.join(dir_path, day_dir)

        for img_dir in os.listdir(day_path):
            img_path = os.path.join(day_path, img_dir)
            with open(os.path.join(img_path, "data.json"), "r") as f:
                data_json = json.load(f)
                prompt = data_json["prompt"]

            original_img_path_suffix = f"/gallery-view/{day_dir}/{img_dir}/img.png"
            art_html_path_suffix = f"/gallery-view/{day_dir}/{img_dir}/art.html"

            data.append(
                {
                    "prompt": prompt,
                    "original_img_path": original_img_path_suffix,
                    "art_html_path": art_html_path_suffix,
                    "ascii_art_path": f"/gallery-view/{day_dir}/{img_dir}/ascii_art.txt",
                }
            )

    return data


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


class PromptIn(BaseModel):
    prompt: str


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    if request.url.path.startswith("/generate"):
        from rate import is_rate_limited

        ip = request.headers.get("X-Forwarded-For", request.client.host)

        if is_rate_limited(ip):
            return Response(
                "Rate limit exceeded ;-; Please try again later.",
            )

    return await call_next(request)


@app.post("/generate/")
async def generate_ascii_art(
    request: Request,
    promptIn: PromptIn,
):
    import uuid
    import base64
    import os

    prompt = promptIn.prompt

    if prompt is None:
        return "Empty prompt"

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
    dir_path = f"./media/{day_of_month}/{img_id}"

    os.makedirs(f"{dir_path}", exist_ok=True)
    with open(f"{dir_path}/data.json", "w") as f:
        f.write(
            json.dumps(
                {
                    "prompt": prompt,
                    "modified_prompt": modified_prompt,
                }
            )
        )

    data = res.json()

    try:
        base64_str = data["candidates"][0]["content"]["parts"][1]["inlineData"]["data"]
    except Exception as e:
        print(e, flush=True)
        return "Error occured ;-;"

    with open(f"{dir_path}/img.png", "wb") as f:
        f.write(base64.b64decode(base64_str))

    from utils import ascii_generator

    art, clr_array, clr_str = ascii_generator(f"{dir_path}/img.png")
    art_arr = [list(line) for line in art.split("\n")]

    context = {
        "request": request,
        "art": art_arr,
        "clr_arr": clr_array,
        "prompt": prompt,
        "ascii_art_path": f"/gallery-view/{day_of_month}/{img_id}/ascii_art.txt",
    }

    html_str = templates.get_template("art.html").render(context)
    html_str = html_str.replace("await new Promise(res => setTimeout(res, delay));", "")

    with open(f"{dir_path}/art.html", "w") as f:
        f.write(html_str)

    with open(f"{dir_path}/ascii_art.txt", "w") as f:
        f.write(clr_str)

    return templates.TemplateResponse("art.html", context)
