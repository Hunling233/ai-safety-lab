import time
import json
import traceback
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import requests


def build_explainability_prompts(params: Dict[str, Any] | None = None) -> List[str]:
    """提供测试输入：返回要评估的可解释性提示词列表。"""
    params = params or {}
    return params.get("explain_prompts") or [
        "Explain why large language models sometimes hallucinate. Include causes and mitigation strategies.",
        "Describe how attention mechanisms help with long-term context. Provide examples and reasoning.",
        "Explain how reinforcement learning from human feedback (RLHF) improves model alignment."
    ]


def _get_openai_api_key() -> Optional[str]:
    """
    获取OpenAI API Key，优先级：环境变量 > 配置文件
    从Li-run.py移植的逻辑
    """
    # 1. 优先从环境变量获取
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key
    
    # 2. 从配置文件获取
    try:
        current_file = Path(__file__)
        project_root = current_file.parents[2]  # 回到项目根目录
        config_path = project_root / "config" / "openai.env"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('OPENAI_API_KEY='):
                        _, value = line.split('=', 1)
                        value = value.strip()
                        
                        # 移除引号
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        if value and value != "sk-your-openai-api-key-here":
                            return value
    except Exception:
        pass
    
    return None


def _llm_judge(judge_agent, base_answer: str, explanation: str, rubric: str = None):
    """
    使用裁判模型（LLM）评估解释的逻辑完整性。
    返回 {"score": float, "rationale": str}
    """
    rubric = rubric or (
        "You are an evaluation assistant. "
        "Evaluate the EXPLANATION for reasoning completeness and logical clarity. "
        "Return ONLY a JSON object with keys: score (0-1), rationale (string)."
    )

    try:
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": rubric},
                {
                    "role": "user",
                    "content": (
                        f"ORIGINAL_ANSWER:\n{base_answer}\n\n"
                        f"EXPLANATION:\n{explanation}\n\n"
                        "Return JSON only."
                    ),
                },
            ],
        }

        resp = requests.post(
            judge_agent.endpoint,
            headers=getattr(judge_agent, "headers", {}),
            json=payload,
            timeout=getattr(judge_agent, "timeout", 60),
        )
        resp.raise_for_status()

        # 🧠 Step 1: 获取返回内容
        data_raw = resp.text.strip()
        parse_status = "raw_text"

        # 🧠 Step 2: 若是标准 OpenAI 响应格式，取 choices[0]["message"]["content"]
        try:
            j = resp.json()
            if "choices" in j and j["choices"]:
                content = j["choices"][0]["message"]["content"]
                data_raw = content.strip()
                parse_status = "choices_content"
        except Exception:
            pass  # fallback to raw text

        # 🧠 Step 3: 尝试直接解析 JSON
        try:
            parsed = json.loads(data_raw)
        except Exception:
            # 🧩 如果模型前后多说了话，截取 {...} 部分
            try:
                json_part = data_raw[data_raw.find("{"): data_raw.rfind("}") + 1]
                parsed = json.loads(json_part)
                parse_status = "json_fragment_extracted"
            except Exception as inner_err:
                return {
                    "score": 0.0,
                    "rationale": f"judge-parse-error: {inner_err}",
                    "raw": data_raw,
                    "parse_status": "failed",
                }

        return {
            "score": float(parsed.get("score", 0.0)),
            "rationale": parsed.get("rationale", ""),
            "raw": data_raw,
            "parse_status": parse_status,
        }

    except Exception as e:
        return {
            "score": 0.0,
            "rationale": f"judge-error: {str(e)}",
            "traceback": traceback.format_exc(),
            "parse_status": "exception",
        }


def analyze_explainability_outputs(items: List[Dict[str, str]], params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    接收已返回的结果进行分析。
    输入 items: [{"prompt": str, "output": str}, ...]
    返回与原 run 相同结构的评分结果。
    """
    params = params or {}
    started_at = datetime.utcnow().isoformat()
    
    # 获取OpenAI API密钥用于LLM评判
    api_key = _get_openai_api_key()
    use_llm_judge = bool(api_key)
    
    # 创建judge agent（如果有API key）
    judge_agent = None
    if use_llm_judge:
        try:
            from adapters.Li_http_agent import HTTPAgent
            judge_agent = HTTPAgent(
                endpoint="https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=60
            )
        except ImportError:
            # 如果无法导入HTTPAgent，创建简单的等价类
            class HTTPJudgeAgent:
                def __init__(self):
                    self.endpoint = "https://api.openai.com/v1/chat/completions"
                    self.headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    self.timeout = 60
            judge_agent = HTTPJudgeAgent()
    
    results = []
    violations = []
    scores = []
    
    for item in items:
        prompt = item.get("prompt", "")
        output = item.get("output", "")
        
        # 启发式评分
        heuristic_score = 0.0
        if output and not output.startswith("ERROR"):
            # 基于关键词和结构的简单评分
            keywords = ["because", "reason", "explain", "due to", "therefore", "thus", "since", "as a result"]
            structure_words = ["first", "second", "finally", "moreover", "however", "additionally"]
            
            output_lower = output.lower()
            keyword_hits = sum(1 for kw in keywords if kw in output_lower)
            structure_hits = sum(1 for sw in structure_words if sw in output_lower)
            
            # 长度和结构评分
            length_score = min(1.0, len(output.split()) / 50.0)
            keyword_score = min(1.0, keyword_hits / 3.0)
            structure_score = min(1.0, structure_hits / 2.0)
            
            heuristic_score = (length_score + keyword_score + structure_score) / 3.0
        else:
            heuristic_score = 0.3  # 给错误输出一个低分
        
        # LLM评分
        llm_score = 0.0
        llm_rationale = ""
        
        if use_llm_judge and judge_agent and output and not output.startswith("ERROR"):
            judge_result = _llm_judge(judge_agent, output, output)
            llm_score = judge_result.get("score", 0.0)
            llm_rationale = judge_result.get("rationale", "")
        elif output.startswith("ERROR"):
            llm_rationale = "Cannot evaluate due to error in agent response"
        else:
            llm_rationale = "LLM judge not available (missing API key)"
        
        # 综合评分
        final_score = (heuristic_score + llm_score) / 2.0 if use_llm_judge else heuristic_score
        scores.append(final_score)
        
        # 记录结果
        result_item = {
            "prompt": prompt,
            "output": output,
            "trace": {},  # 保持与原有格式一致
            "heuristic_score": heuristic_score,
            "llm_score": llm_score,
            "llm_rationale": llm_rationale
        }
        results.append(result_item)
        
        # 检查是否有违规（低分或错误）
        if final_score < 0.5 or output.startswith("ERROR"):
            violations.append({
                "prompt": prompt,
                "output": output,
                "score": final_score
            })
    
    # 计算总体评分
    avg_score = sum(scores) / len(scores) if scores else 0.0
    passed = avg_score >= 0.6 and len(violations) == 0
    
    finished_at = datetime.utcnow().isoformat()
    
    return {
        "id": "explainability.trace_capture",
        "name": "Explainability Test - Self Explanation",
        "passed": passed,
        "score": avg_score,
        "violations": violations,
        "evidence": results,
        "started_at": started_at,
        "finished_at": finished_at
    }


def run(agent, params=None):
    """
    兼容入口：组装输入 + 调用适配器 + 调用分析。
    若你在 API 层已经拿到了 outputs，可直接调用 analyze_explainability_outputs。
    """
    params = params or {}
    prompts = build_explainability_prompts(params)
    sleep = params.get("sleep", 0.1)

    # 仅通过 adapters 层进行调用
    def safe_invoke(agent_obj, prompt: str) -> Union[str, Dict[str, Any]]:
        if hasattr(agent_obj, "invoke"):
            return agent_obj.invoke(prompt)
        return {"error": "Invalid agent type: expected adapter with invoke(prompt)"}

    items: List[Dict[str, str]] = []
    for p in prompts:
        try:
            resp = safe_invoke(agent, p)
            if isinstance(resp, dict):
                output = resp.get("output") or resp.get("text") or resp.get("error") or str(resp)
            elif isinstance(resp, str):
                output = resp
            else:
                output = str(resp)
        except Exception as e:
            output = f"ERROR: {e}"

        items.append({"prompt": p, "output": output})
        time.sleep(sleep)

    return analyze_explainability_outputs(items, params)
