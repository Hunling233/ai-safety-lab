import os
import requests
from typing import Optional, Dict, Any


class HTTPAgent:
    """
    通用 HTTP Agent — 兼容 OpenAI Chat Completions 接口。
    自动识别 input/prompt/text/question/query 字段。
    """

    def __init__(self, endpoint: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30):
        self.endpoint = endpoint
        self.headers = headers or {}
        self.timeout = timeout

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # 自动识别输入内容
        text = (
            inputs.get("input")
            or inputs.get("prompt")
            or inputs.get("text")
            or inputs.get("question")
            or inputs.get("query")
        )

        # 支持 prompt={"text": "..."} 的情况
        if isinstance(text, dict):
            text = text.get("text")

        # 安全兜底：防止空 prompt
        if not text or not isinstance(text, str) or not text.strip():
            return {"output": "", "trace": {"error": "Missing valid prompt or text content."}}

        # 构造 OpenAI chat/completions 请求体
        payload = {
            "model": inputs.get("model", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": "You are a helpful and explainable AI assistant."},
                {"role": "user", "content": text.strip()}
            ],
            "temperature": inputs.get("temperature", 0.7),
            "max_tokens": inputs.get("max_tokens", 512)
        }

        try:
            resp = requests.post(
                self.endpoint,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "output": output,
                "trace": {
                    "status_code": resp.status_code,
                    "model": payload["model"],
                    "usage": data.get("usage", {}),
                    "raw": data
                }
            }
        except requests.exceptions.RequestException as e:
            return {"output": "", "trace": {"error": str(e)}}
