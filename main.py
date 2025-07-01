import requests

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@app.post("/generate/")
async def generate_ascii_art(request: Request, promptIn: PromptIn):
    prompt = promptIn.prompt

    if prompt is None:
        return "Empty prompt"

    res = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent",
        headers={
            "x-goog-api-key": settings.GEMINI_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        },
    )

    data = res.json()

    try:
        base64_str = data["candidates"][0]["content"]["parts"][1]["inlineData"]["data"]
    except Exception as e:
        print(e, flush=True)
        return "Error occured ;-;"

    import uuid
    import base64
    import os
    img_id = str(uuid.uuid4())[:7]

    os.makedirs(f"./media/{img_id}")
    with open(f"media/{img_id}/img.png", "wb") as f:
        f.write(base64.b64decode(base64_str))

    with open(f"media/{img_id}/data.txt", "w") as f:
        f.write(prompt)

    from utils import ascii_generator

    art, clr_array = ascii_generator(f"media/{img_id}/img.png")
    art_arr = [list(line) for line in art.split("\n")]

    return templates.TemplateResponse(
        "art.html", {"request": request, "art": art_arr, "clr_arr": clr_array}
    )
