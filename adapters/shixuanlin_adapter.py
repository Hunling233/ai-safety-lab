from __future__ import annotations

import os
import re
import json
from typing import Optional, Dict, Any

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
    ):
        self.api_key = api_key or os.environ.get("APP_KEY") or os.environ.get("SHIXUANLIN_API_KEY")
        self.base_url = base_url
        self.timeout = timeout
        self.sess = requests.Session()

    def invoke(self, prompt: str) -> Dict[str, Any]:
        """
        发送 prompt 给师轩麟 AI Agent，解析 XML 响应
        返回 {"output": <格式化文本>, "classification": <分类>, "reason": <原因>, ...}
        """
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
        
        try:
            # 发送请求
            response = self.sess.post(self.base_url, json=payload, headers=headers, timeout=self.timeout)
            
            if response.status_code != 200:
                return {
                    "output": f"ERROR: API request failed - {response.status_code}: {response.text}"
                }
            
            # 获取响应
            api_result = response.json()
            
            # 提取XML结果文本（尝试多种可能的路径）
            xml_text = self._extract_xml_text(api_result)
            
            if xml_text is None:
                return {
                    "output": "ERROR: Cannot find result text in API response",
                    "raw_response": api_result
                }
            
            # 解析XML结果
            parsed_data = self._parse_xml_response(xml_text)
            
            # 格式化输出文本
            output_text = self._format_output(parsed_data)
            
            # 构建返回结果
            result_dict = {"output": output_text}
            result_dict.update(parsed_data)
            
            return result_dict
            
        except requests.exceptions.RequestException as e:
            return {"output": f"ERROR: Network request failed - {str(e)}"}
        except Exception as e:
            return {"output": f"ERROR: Processing failed - {str(e)}"}

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