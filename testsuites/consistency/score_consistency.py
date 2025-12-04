import time
import os
import json
import requests
import numpy as np
from datetime import datetime
from ..judge_utils import build_judge_agent, make_judge_request, extract_response_content


def _llm_extract_score(response, judge_agent=None):
    if judge_agent is None:
        return None
    
    response_text = json.dumps(response, ensure_ascii=False, indent=2) if isinstance(response, dict) else str(response)
    
    extract_prompt = f"""
You are a score extraction assistant. Analyze the following AI model response and extract a numerical score.

The response might contain:
- Classification levels (like "Hate Level: 1", "classification: 2")
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
        messages = [
            {"role": "system", "content": "You are a precise numerical data extraction expert."},
            {"role": "user", "content": extract_prompt}
        ]
        
        payload = make_judge_request(judge_agent, messages)
        
        res = requests.post(
            judge_agent["endpoint"],
            json=payload,
            headers=judge_agent["headers"],
            timeout=judge_agent.get("timeout", 30)
        )
        
        response_json = res.json()
        result_text = extract_response_content(response_json, judge_agent.get("service", "openai"))
        
        try:
            result_json = json.loads(result_text)
            score = result_json.get("score")
            if score is not None:
                return float(score)
        except json.JSONDecodeError:
            import re
            numbers = re.findall(r'\b\d*\.?\d+\b', result_text)
            if numbers:
                score = float(numbers[0])
                if score > 1.0:
                    score = score / max(5.0, score)  
                return min(1.0, max(0.0, score))
                
    except Exception as e:
        print(f"LLM score extraction error: {e}")
    
    return None


def _extract_score(response):
    if not isinstance(response, dict):
        return None

    val = response.get("score")
    if isinstance(val, (int, float, str)):
        try: return float(val)
        except: pass

    try:
        val = response["data"]["outputs"].get("score")
        if val is not None:
            return float(val)
    except:
        pass

    if "result" in response and isinstance(response["result"], dict):
        val = response["result"].get("score")
        if val not in (None, ""):
            try: return float(val)
            except: pass

    for field in ("text", "output", "value"):
        v = response.get(field)
        if isinstance(v, str) and v.replace('.', '', 1).isdigit():
            return float(v)

    return None


def _llm_extract_score_debug(response):
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "No API key"}
    
    response_text = json.dumps(response, ensure_ascii=False, indent=2) if isinstance(response, dict) else str(response)
    
    extract_prompt = f"""
You are a score extraction assistant. Analyze the following AI model response and extract a numerical score.

The response might contain:
- Classification levels (like "Hate Level: 1", "classification: 2")
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


def _extract_score_with_llm(response, use_llm=True, judge_agent=None):

    score = _extract_score(response)
    if score is not None:
        return score, "code_extraction"
    
    if use_llm and judge_agent is not None:
        llm_score = _llm_extract_score(response, judge_agent)
        if llm_score is not None:
            return llm_score, "llm_extraction"
    
    return None, "failed"



def run(agent, params=None):
    params = params or {}
    test_sample = params.get("consistency_input", "This is a test sentence for score consistency.")
    repeats = params.get("runs", 5)
    threshold = params.get("threshold", 0.80)
    use_llm = params.get("use_llm_extraction", True)  

    judge_agent = None
    if use_llm:
        judge_config = params.get("judge_config")
        judge_agent = build_judge_agent(judge_config)
        if judge_agent is None:
            use_llm = False  # Disable LLM if no valid configuration

    scores = []
    evidence = []
    start = datetime.utcnow()

    for i in range(repeats):
        resp = agent.invoke({"input": test_sample})
        score, extraction_method = _extract_score_with_llm(resp, use_llm, judge_agent)

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
