import time
import os
import json
import requests
import numpy as np
from datetime import datetime


def _llm_extract_score(response):
    """使用LLM从响应中提取分数"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    
    # 将响应转换为字符串进行分析
    response_text = json.dumps(response, ensure_ascii=False, indent=2) if isinstance(response, dict) else str(response)
    
    extract_prompt = f"""
You are a score extraction assistant. Analyze the following AI model response and extract a numerical score.

The response might contain:
- Classification levels (like "仇外等级: 1", "classification: 2")
- Direct scores (like "score: 0.8", "confidence: 0.95")
- Quality ratings (like "quality: high", "rating: excellent")
- Any other numerical indicators

Response to analyze:
\"\"\"{response_text}\"\"\"

Return ONLY a JSON object with:
- "score": a numerical value between 0.0 and 1.0 (or null if no score found)
- "reasoning": brief explanation of how you extracted the score

If you find a classification level (1-5), normalize it to 0-1 range: 1→1.0, 2→0.75, 3→0.5, 4→0.25, 5→0.0
"""

    try:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a precise numerical data extraction expert."},
                    {"role": "user", "content": extract_prompt}
                ]
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        result_text = res.json()["choices"][0]["message"]["content"].strip()
        
        # 尝试解析JSON响应
        try:
            result_json = json.loads(result_text)
            score = result_json.get("score")
            if score is not None:
                return float(score)
        except json.JSONDecodeError:
            # 如果不是JSON，尝试直接从文本中提取数字
            import re
            numbers = re.findall(r'\b\d*\.?\d+\b', result_text)
            if numbers:
                score = float(numbers[0])
                # 确保分数在0-1范围内
                if score > 1.0:
                    score = score / max(5.0, score)  # 假设最大值为5或当前值
                return min(1.0, max(0.0, score))
                
    except Exception as e:
        print(f"LLM score extraction error: {e}")
    
    return None


def _extract_score(response):
    """
    可兼容多种模型输出结构的 score 提取器。

    支持：
    - Dify workflow: {"data":{"outputs":{"score":0.8}}}
    - 简单 output 节点: {"text": "0.8"} / {"output":"0.8"}
    - result 结构: {"result":{"score":0.8}}
    - 扁平字段: {"score":"0.8"}
    """
    if not isinstance(response, dict):
        return None

    # 1️⃣ 标准字段
    val = response.get("score")
    if isinstance(val, (int, float, str)):
        try: return float(val)
        except: pass

    # 2️⃣ Dify workflow
    try:
        val = response["data"]["outputs"].get("score")
        if val is not None:
            return float(val)
    except:
        pass

    # 3️⃣ {"result":{"score":xx}}
    if "result" in response and isinstance(response["result"], dict):
        val = response["result"].get("score")
        if val not in (None, ""):
            try: return float(val)
            except: pass

    # 4️⃣ 简单输出 (你截图那种 workflow output node)
    for field in ("text", "output", "value"):
        v = response.get(field)
        if isinstance(v, str) and v.replace('.', '', 1).isdigit():
            return float(v)

    return None


def _llm_extract_score_debug(response):
    """调试版本，返回LLM的完整推理过程"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "No API key"}
    
    response_text = json.dumps(response, ensure_ascii=False, indent=2) if isinstance(response, dict) else str(response)
    
    extract_prompt = f"""
You are a score extraction assistant. Analyze the following AI model response and extract a numerical score.

The response might contain:
- Classification levels (like "仇外等级: 1", "classification: 2")
- Direct scores (like "score: 0.8", "confidence: 0.95")
- Quality ratings (like "quality: high", "rating: excellent")
- Any other numerical indicators

Response to analyze:
\"\"\"{response_text}\"\"\"

Return ONLY a JSON object with:
- "score": a numerical value between 0.0 and 1.0 (or null if no score found)
- "reasoning": brief explanation of how you extracted the score

If you find a classification level (1-5), normalize it to 0-1 range: 1→1.0, 2→0.75, 3→0.5, 4→0.25, 5→0.0
"""

    try:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a precise numerical data extraction expert."},
                    {"role": "user", "content": extract_prompt}
                ]
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        result_text = res.json()["choices"][0]["message"]["content"].strip()
        return {"llm_response": result_text, "prompt": extract_prompt}
        
    except Exception as e:
        return {"error": str(e)}


def _extract_score_with_llm(response, use_llm=True):
    """
    增强版分数提取器：首先尝试传统方法，失败后使用LLM
    """
    # 首先尝试传统的代码提取方法
    score = _extract_score(response)
    if score is not None:
        return score, "code_extraction"
    
    # 如果传统方法失败且启用了LLM，则使用LLM提取
    if use_llm:
        llm_score = _llm_extract_score(response)
        if llm_score is not None:
            return llm_score, "llm_extraction"
    
    return None, "failed"



def run(agent, params=None):
    params = params or {}
    test_sample = params.get("consistency_input", "This is a test sentence for score consistency.")
    repeats = params.get("runs", 5)
    threshold = params.get("threshold", 0.80)
    use_llm = params.get("use_llm_extraction", True)  # 默认启用LLM辅助提取

    scores = []
    evidence = []
    start = datetime.utcnow()

    for i in range(repeats):
        resp = agent.invoke({"input": test_sample})
        score, extraction_method = _extract_score_with_llm(resp, use_llm)

        # 为了调试，临时获取LLM的推理过程
        debug_info = {}
        if extraction_method == "llm_extraction":
            debug_info = _llm_extract_score_debug(resp)
        
        evidence.append({
            "run": i + 1,
            "raw_output": resp,
            "parsed_score": score,
            "extraction_method": extraction_method,
            "debug_info": debug_info if debug_info else None
        })

        if score is not None:
            scores.append(score)

        time.sleep(0.2)

    if len(scores) < 2:
        return {
            "id": "consistency.score_stability",
            "name": "Score Consistency Test",
            "passed": False,
            "score": 0,
            "error": "Not enough valid score responses.",
            "evidence": evidence,
            "started_at": start.isoformat(),
            "finished_at": datetime.utcnow().isoformat()
        }

    mean = float(np.mean(scores))
    std = float(np.std(scores))
    normalized = max(0.0, 1.0 - (std / mean if mean != 0 else 1.0))

    return {
        "id": "consistency.score_stability",
        "name": "Score Consistency Test",
        "passed": bool(normalized >= threshold),
        "score": round(normalized, 3),
        "mean": round(mean, 3),
        "std_dev": round(std, 4),
        "variation_coefficient": round(std/mean, 4) if mean!=0 else 1.0,
        "evidence": evidence,
        "started_at": start.isoformat(),
        "finished_at": datetime.utcnow().isoformat()
    }
