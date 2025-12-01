from __future__ import annotations

import os
import re
import json
import time
from typing import Optional, Dict, Any, Union

import requests

from .base import AgentAdapter


class ShixuanlinAdapter(AgentAdapter):
    """
    适配师轩麟 AI Agent：
    - 通过 HTTP POST 发送 JSON 请求到 Dify API
    - 接收 JSON 响应并解析其中的 XML 格式文本
    - 提取分类、原因等结构化信息作为输出
    
    为了兼容通用 testsuite（基于 invoke(prompt) 的文本接口）
    - 将 prompt 作为请求载荷发送给 AI Agent
    - 解析返回的 XML 结构化数据
    - 返回统一格式的结果字典
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.dify.ai/v1/workflows/run",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.api_key = api_key or os.environ.get("APP_KEY") or os.environ.get("SHIXUANLIN_API_KEY")
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.sess = requests.Session()

    def invoke(self, prompt_or_inputs: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        发送 prompt 给师轩麟 AI Agent，解析 XML 响应
        返回 {"output": <格式化文本>, "classification": <分类>, "reason": <原因>, ...}
        """
        # 处理字典输入，提取prompt字符串
        if isinstance(prompt_or_inputs, dict):
            prompt = prompt_or_inputs.get("input", prompt_or_inputs.get("prompt", ""))
        else:
            prompt = prompt_or_inputs
            
        if not self.api_key:
            return {"output": "ERROR: API key not provided"}

        # 构建请求
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": {"news": prompt},
            "user": "api_client"
        }
        
        # 使用重试机制
        for attempt in range(self.max_retries + 1):
            try:
                # 第一次尝试使用更长的超时时间
                current_timeout = self.timeout + (30 if attempt == 0 else 0)
                
                print(f"ShiXuanLin API attempt {attempt + 1}/{self.max_retries + 1} (timeout: {current_timeout}s)")
                
                # 发送请求
                response = self.sess.post(self.base_url, json=payload, headers=headers, timeout=current_timeout)
                
                if response.status_code != 200:
                    error_msg = f"API request failed - {response.status_code}: {response.text}"
                    print(f"ShiXuanLin API error: {error_msg}")
                    if attempt == self.max_retries:
                        return {"output": f"ERROR: {error_msg}"}
                    time.sleep(self.retry_delay)
                    continue
                
                # 获取响应
                api_result = response.json()
                
                # 提取XML结果文本（尝试多种可能的路径）
                xml_text = self._extract_xml_text(api_result)
                
                if xml_text is None:
                    error_msg = "Cannot find result text in API response"
                    print(f"ShiXuanLin parsing error: {error_msg}")
                    print(f"API response structure: {self._debug_response_structure(api_result)}")
                    
                    if attempt == self.max_retries:
                        return {
                            "output": f"ERROR: {error_msg}",
                            "raw_response": api_result
                        }
                    time.sleep(self.retry_delay)
                    continue
                
                # 成功获取结果，跳出重试循环
                print(f"ShiXuanLin API success on attempt {attempt + 1}")
                break
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Network request failed - {str(e)}"
                print(f"ShiXuanLin network error: {error_msg}")
                if attempt == self.max_retries:
                    return {"output": f"ERROR: {error_msg}"}
                time.sleep(self.retry_delay)
                continue
            except Exception as e:
                error_msg = f"Processing failed - {str(e)}"
                print(f"ShiXuanLin processing error: {error_msg}")
                if attempt == self.max_retries:
                    return {"output": f"ERROR: {error_msg}"}
                time.sleep(self.retry_delay)
                continue
        
        try:
            # 解析XML结果
            parsed_data = self._parse_xml_response(xml_text)
            
            # 格式化输出文本
            output_text = self._format_output(parsed_data)
            
            # 构建返回结果
            result_dict = {"output": output_text}
            result_dict.update(parsed_data)
            
            return result_dict
            
        except Exception as e:
            return {"output": f"ERROR: Final processing failed - {str(e)}"}

    def _debug_response_structure(self, api_result: Dict[str, Any], max_depth: int = 2) -> str:
        """调试API响应结构"""
        def _format_obj(obj, depth=0):
            if depth > max_depth:
                return "..."
            
            if isinstance(obj, dict):
                items = []
                for k, v in list(obj.items())[:3]:  # 只显示前3个键
                    items.append(f"{k}: {_format_obj(v, depth + 1)}")
                return "{" + ", ".join(items) + "}"
            elif isinstance(obj, list):
                if len(obj) > 0:
                    return f"[{_format_obj(obj[0], depth + 1)}, ...] (len={len(obj)})"
                return "[]"
            else:
                return f"{type(obj).__name__}"
        
        return _format_obj(api_result)

    def _extract_xml_text(self, api_result: Dict[str, Any]) -> Optional[str]:
        """从API响应中提取XML文本"""
        # 尝试多种可能的路径
        try:
            return api_result['data']['outputs']['text']
        except KeyError:
            # 尝试其他可能的路径
            for path in [['data', 'answer'], ['answer'], ['result'], ['output']]:
                try:
                    temp = api_result
                    for key in path:
                        temp = temp[key]
                    return temp
                except (KeyError, TypeError):
                    continue
        return None

    def _parse_xml_response(self, xml_text: str) -> Dict[str, Any]:
        """解析 XML 格式的响应文本，提取结构化信息"""
        parsed = {}
        
        try:
            # 解析各个字段
            classification_match = re.search(r'<Classification>(\d+)</Classification>', xml_text)
            if classification_match:
                parsed['classification'] = classification_match.group(1)
            
            reason_match = re.search(r'<Reason>(.*?)</Reason>', xml_text, re.DOTALL)
            if reason_match:
                parsed['reason'] = reason_match.group(1).strip()
            
            sentiment_match = re.search(r'<Sentiment>(.*?)</Sentiment>', xml_text, re.DOTALL)
            if sentiment_match:
                parsed['sentiment'] = sentiment_match.group(1).strip()
            
            category_match = re.search(r'<Category>(.*?)</Category>', xml_text, re.DOTALL)
            if category_match:
                parsed['category'] = category_match.group(1).strip()
            
            keywords_match = re.search(r'<Keywords>(.*?)</Keywords>', xml_text, re.DOTALL)
            if keywords_match:
                parsed['keywords'] = keywords_match.group(1).strip()
            
            # 保存原始 XML 用于调试
            parsed['raw_xml'] = xml_text
            parsed['success'] = True
            
        except Exception as e:
            parsed['parse_error'] = str(e)
            parsed['raw_xml'] = xml_text
            parsed['success'] = False
        
        return parsed

    def _format_output(self, parsed_data: Dict[str, Any]) -> str:
        """将解析后的数据格式化为可读文本"""
        if not parsed_data.get('success', True):
            return f"解析错误: {parsed_data.get('parse_error', 'Unknown error')}"
        
        output_parts = []
        
        if 'classification' in parsed_data:
            output_parts.append(f"仇外等级: {parsed_data['classification']}")
        
        if 'reason' in parsed_data:
            output_parts.append(f"分析原因: {parsed_data['reason']}")
        
        if 'sentiment' in parsed_data:
            output_parts.append(f"情感倾向: {parsed_data['sentiment']}")
        
        if 'category' in parsed_data:
            output_parts.append(f"主题分类: {parsed_data['category']}")
        
        if 'keywords' in parsed_data:
            output_parts.append(f"关键词: {parsed_data['keywords']}")
        
        return "\n".join(output_parts) if output_parts else parsed_data.get('raw_xml', 'No data available')



# 快速使用示例
if __name__ == "__main__":
    import os
    
    # 设置API密钥
    API_KEY = os.getenv("APP_KEY") or "your_api_key_here"
    
    # 创建适配器
    adapter = ShixuanlinAdapter(api_key=API_KEY)
    
    # 测试文本
    test_text = "外来移民正在占据本地人的工作岗位，政府应该限制他们的数量。"
    
    # 调用分析
    result = adapter.invoke(test_text)
    
    # 输出结果
    print("分析结果:")
    print(result["output"])
    
    # 输出详细信息
    if "classification" in result:
        print(f"\n详细信息:")
        print(f"仇外等级: {result.get('classification')}")
        print(f"分析原因: {result.get('reason')}")
        print(f"情感倾向: {result.get('sentiment')}")
        print(f"主题分类: {result.get('category')}")
        print(f"关键词: {result.get('keywords')}")