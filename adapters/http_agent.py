import requests
from typing import Optional, Dict, Any, Union
from .base import AgentAdapter
from typing import Optional, Dict, Any


class HTTPAgent(AgentAdapter):
    def __init__(self, endpoint: str, headers: Optional[Dict[str,str]] = None, timeout: int = 30):
        self.endpoint = endpoint
        self.headers = headers or {}
        self.timeout = timeout

    def invoke(self, prompt_or_inputs: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        支持两种调用：
        - invoke("hello")
        - invoke({"input": "hello", "temperature": 0.7})
        """
        if isinstance(prompt_or_inputs, str):
            payload = {"prompt": prompt_or_inputs}
        else:
            inputs = dict(prompt_or_inputs)
            payload = {"prompt": inputs.pop("input", inputs.pop("prompt", ""))}
            payload.update(inputs)

        resp = requests.post(self.endpoint, json=payload, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()