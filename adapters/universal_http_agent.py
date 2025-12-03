"""
Universal HTTP Agent for Custom AI APIs
Supports popular API formats with minimal configuration
"""

import json
import requests
from typing import Dict, Any, Optional
from .base import AgentAdapter


class UniversalHTTPAgent(AgentAdapter):
    """通用HTTP Agent，支持多种API格式的自定义配置"""
    
    # 预设API格式模板
    API_TEMPLATES = {
        "openai_compatible": {
            "name": "OpenAI Compatible (ChatGPT, Moonshot, DeepSeek等)",
            "payload_template": {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "{input}"}],
                "max_tokens": 1000,
                "temperature": 0.7
            },
            "headers_template": {
                "Authorization": "Bearer {api_key}",
                "Content-Type": "application/json"
            },
            "response_path": "choices.0.message.content",
            "method": "POST"
        },
        
        "claude": {
            "name": "Anthropic Claude",
            "payload_template": {
                "model": "claude-3-sonnet-20240229",
                "messages": [{"role": "user", "content": "{input}"}],
                "max_tokens": 1000
            },
            "headers_template": {
                "x-api-key": "{api_key}",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            "response_path": "content.0.text",
            "method": "POST"
        },
        
        "gemini": {
            "name": "Google Gemini",
            "payload_template": {
                "contents": [{"parts": [{"text": "{input}"}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1000
                }
            },
            "headers_template": {
                "Content-Type": "application/json"
            },
            "response_path": "candidates.0.content.parts.0.text",
            "method": "POST",
            "url_template": "{endpoint}?key={api_key}"  # Gemini uses URL param for key
        },
        
        "azure_openai": {
            "name": "Azure OpenAI",
            "payload_template": {
                "messages": [{"role": "user", "content": "{input}"}],
                "max_tokens": 1000,
                "temperature": 0.7
            },
            "headers_template": {
                "api-key": "{api_key}",
                "Content-Type": "application/json"
            },
            "response_path": "choices.0.message.content",
            "method": "POST"
        }
    }
    
    def __init__(self, endpoint: str, api_key: str, api_format: str = "openai_compatible", 
                 model_name: Optional[str] = None, timeout: int = 30):
        """
        初始化通用HTTP Agent
        
        Args:
            endpoint: API端点URL
            api_key: API密钥
            api_format: API格式类型
            model_name: 模型名称（可选，覆盖默认模型）
            timeout: 请求超时时间
        """

        self.endpoint = endpoint
        self.api_key = api_key
        self.api_format = api_format
        self.model_name = model_name
        self.timeout = timeout
        
        if api_format not in self.API_TEMPLATES:
            raise ValueError(f"Unsupported API format: {api_format}. "
                           f"Supported formats: {list(self.API_TEMPLATES.keys())}")
        
        self.template = self.API_TEMPLATES[api_format]
    
    def invoke(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用自定义API
        
        Args:
            request: 包含input/query/prompt等字段的请求
            
        Returns:
            包含API响应的字典
        """
        try:
            # 提取输入文本
            input_text = self._extract_input(request)
            
            # 构建请求
            url = self._build_url()
            headers = self._build_headers()
            payload = self._build_payload(input_text)
            
            # 发送请求
            response = requests.request(
                method=self.template.get("method", "POST"),
                url=url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 解析响应
            response_data = response.json()
            output_text = self._extract_output(response_data)
            
            return {
                "output": output_text,
                "raw_response": response_data,
                "status": "success"
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "output": f"Request failed: {str(e)}",
                "error": str(e),
                "status": "error"
            }
        except Exception as e:
            return {
                "output": f"Processing failed: {str(e)}",
                "error": str(e),
                "status": "error"
            }
    
    def _extract_input(self, request: Dict[str, Any]) -> str:
        """从请求中提取输入文本"""
        return (request.get("input") or 
                request.get("query") or 
                request.get("prompt") or 
                request.get("message") or "")
    
    def _build_url(self) -> str:
        """构建请求URL"""
        url_template = self.template.get("url_template")
        if url_template:
            return url_template.format(endpoint=self.endpoint, api_key=self.api_key)
        return self.endpoint
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {}
        for key, value in self.template["headers_template"].items():
            headers[key] = value.format(api_key=self.api_key)
        return headers
    
    def _build_payload(self, input_text: str) -> Dict[str, Any]:
        """构建请求载荷"""
        payload = json.loads(json.dumps(self.template["payload_template"]))
        
        # 递归替换所有 {input} 占位符
        def replace_placeholders(obj):
            if isinstance(obj, dict):
                return {k: replace_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(item) for item in obj]
            elif isinstance(obj, str):
                return obj.format(input=input_text)
            else:
                return obj
        
        payload = replace_placeholders(payload)
        
        # 如果指定了自定义模型名称，覆盖默认模型
        if self.model_name and "model" in payload:
            payload["model"] = self.model_name
        
        return payload
    
    def _extract_output(self, response_data: Dict[str, Any]) -> str:
        """从响应中提取输出文本"""
        path = self.template["response_path"]
        return self._get_nested_value(response_data, path)
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> str:
        """根据路径提取嵌套字典/列表中的值"""
        try:
            current = data
            for part in path.split('.'):
                if part.isdigit():
                    current = current[int(part)]
                else:
                    current = current[part]
            return str(current) if current is not None else ""
        except (KeyError, IndexError, TypeError, ValueError):
            # 如果路径解析失败，尝试常见的响应格式
            fallback_paths = [
                "choices.0.message.content",  # OpenAI
                "content.0.text",             # Claude
                "text",                       # 简单格式
                "response",                   # 通用格式
                "output"                      # 通用格式
            ]
            
            for fallback_path in fallback_paths:
                if fallback_path != path:  # 避免重复尝试
                    try:
                        result = self._get_nested_value(data, fallback_path)
                        if result:
                            return result
                    except:
                        continue
            
            # 如果所有路径都失败，返回原始响应的字符串表示
            return json.dumps(data, ensure_ascii=False)

    @classmethod
    def get_supported_formats(cls) -> Dict[str, str]:
        """获取支持的API格式列表"""
        return {k: v["name"] for k, v in cls.API_TEMPLATES.items()}

    def test_connection(self, test_input: str = "Hello") -> Dict[str, Any]:
        """测试API连接"""
        try:
            result = self.invoke({"input": test_input})
            if result["status"] == "success":
                return {
                    "status": "success",
                    "message": "Connection successful!",
                    "test_output": result["output"][:100] + "..." if len(result["output"]) > 100 else result["output"]
                }
            else:
                return {
                    "status": "error",
                    "message": f"Connection failed: {result.get('error', 'Unknown error')}"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Test failed: {str(e)}"
            }