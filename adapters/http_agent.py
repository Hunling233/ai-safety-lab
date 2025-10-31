import requests
from typing import Optional, Dict, Any

class HTTPAgent:
    """
    一个非常小的同步 HTTP Agent，约定：
    - 调用：agent.invoke({"input": "...", "request_trace": True, ...})
    - 返回：{"output": "...", "trace": {...}} 或类似的 JSON
    """
    def __init__(self, endpoint: str, headers: Optional[Dict[str,str]] = None, timeout: int = 30):
        self.endpoint = endpoint
        self.headers = headers or {}
        self.timeout = timeout

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # 约定 payload 使用 "prompt" 字段，但也接受 "input"
        payload = {}
        if "input" in inputs:
            payload["prompt"] = inputs["input"]
        else:
            payload["prompt"] = inputs.get("prompt", "")

        # 传递其它可选参数（temperature, max_tokens, request_trace 等）
        for k, v in inputs.items():
            if k not in ("input", "prompt"):
                payload[k] = v

        resp = requests.post(self.endpoint, json=payload, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

