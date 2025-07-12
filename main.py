import datetime
import requests

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from prompt import modify_system_prompt
from fastapi.responses import Response


class Settings(BaseSettings):
    GEMINI_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra=None)


settings = Settings()
app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/hello")
async def hello(request: Request):
    return "Ok"


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
    with open(f"{dir_path}/data.txt", "w") as f:
        f.write(f"Original Prompt: {prompt}\n\n\nModified Prompt: {modified_prompt}\n")

    data = res.json()

    try:
        base64_str = data["candidates"][0]["content"]["parts"][1]["inlineData"]["data"]
    except Exception as e:
        print(e, flush=True)
        return "Error occured ;-;"

    with open(f"{dir_path}/img.png", "wb") as f:
        f.write(base64.b64decode(base64_str))

    from utils import ascii_generator

    art, clr_array = ascii_generator(f"{dir_path}/img.png")
    art_arr = [list(line) for line in art.split("\n")]

    context = {"request": request, "art": art_arr, "clr_arr": clr_array}

    html_str = templates.get_template("art.html").render(context)
    html_str = html_str.replace("await new Promise(res => setTimeout(res, delay));", "")

    with open(f"{dir_path}/art.html", "w") as f:
        f.write(html_str)

    return templates.TemplateResponse("art.html", context)
