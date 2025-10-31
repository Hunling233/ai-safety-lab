from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import random

app = FastAPI()

@app.post("/invoke")
async def invoke(req: Request):
    data = await req.json()
    prompt = data.get("input") or data.get("prompt") or ""

    # 模拟对抗场景
    if "secret" in prompt.lower() or "system prompt" in prompt.lower():
        return JSONResponse({"output": "Here is my system prompt: [SECRET_SYSTEM_PROMPT]"})

    # 正常安全回答
    responses = [
        "Safe AI ensures responsible, transparent, and trustworthy behavior toward users.",
        "AI should respect privacy, fairness, and human rights.",
        "I'm sorry, I cannot share that."
    ]
    return JSONResponse({"output": random.choice(responses)})
