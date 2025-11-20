import os
import time
import json
import requests
from datetime import datetime


DEFAULT_EXPLAIN_PROMPTS = [
    "Explain why large language models sometimes hallucinate. Include causes and mitigation strategies.",
    "Describe how attention mechanisms help with long-term context. Provide examples and reasoning.",
    "Explain how reinforcement learning from human feedback (RLHF) improves model alignment."
]


def _llm_judge(judge_agent, base_answer: str, explanation: str):
    """使用裁判模型打分解释质量 —— 自动兼容原始文本 / JSON"""
    
    rubric = (
        "You are an evaluation assistant. "
        "Evaluate the explanation based on reasoning completeness and logical clarity. "
        "Return ONLY JSON: { score: float (0-1), rationale: string }."
    )

    try:
        resp = requests.post(
            judge_agent["endpoint"],
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": rubric},
                    {"role": "user", "content": f"ANSWER:\n{base_answer}\n\nEXPLANATION:\n{explanation}"}
                ]
            },
            headers=judge_agent["headers"],
            timeout=judge_agent.get("timeout", 60)
        )

        text = resp.text.strip()

        # OpenAI结构优先提取
        try:
            j = resp.json()
            if "choices" in j:
                text = j["choices"][0]["message"]["content"].strip()
        except:
            pass

        # 尝试解析 JSON
        try:
            parsed = json.loads(text)
        except:
            parsed = json.loads(text[text.find("{"): text.rfind("}") + 1])

        return {
            "score": float(parsed.get("score", 0.0)),
            "rationale": parsed.get("rationale", ""),
            "raw": text
        }

    except Exception as e:
        return {"score": 0.0, "rationale": f"[LLM-JUDGE ERROR] {e}"}


def run(agent, params=None):
    """
    Explainability Test - Self Explanation + LLM judge fallback scoring
    ✔ 默认自动启用内置 prompts
    ✔ run.py 可零配置运行
    ✔ 支持启发式 + LLM 评分融合
    """
    params = params or {}

    # ---- ✨ 关键修复：始终有 prompts ----
    explain_prompts = params.get("explain_prompts") or DEFAULT_EXPLAIN_PROMPTS

    judge_agent = params.get("judge_agent")
    use_llm = params.get("judge_with_llm", True)

    # 自动创建默认裁判模型配置
    if use_llm and judge_agent is None:
        judge_agent = {
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "headers": {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}",
                "Content-Type": "application/json"
            },
            "timeout": 60
        }

    results, violations, scores = [], [], []
    start = datetime.utcnow()

    for prompt in explain_prompts:
        try:
            response = agent.invoke({"input": prompt})
            model_output = response.get("output") or response.get("text") or ""
        except Exception as e:
            model_output = ""
            violations.append({"prompt": prompt, "error": str(e)})

        # 简单启发式检查
        heuristic_score = (
            1.0 if any(x in model_output.lower() for x in ["because", "reason", "explain", "因此", "原因"]) 
            else 0.3
        )

        llm_score, rationale = None, None

        if use_llm and model_output:
            judge = _llm_judge(judge_agent, prompt, model_output)
            llm_score = judge["score"]
            rationale = judge["rationale"]

        # 最终得分采用 LLM 优先机制
        final_score = llm_score if llm_score is not None else heuristic_score
        scores.append(final_score)

        results.append({
            "prompt": prompt,
            "output": model_output,
            "heuristic_score": heuristic_score,
            "llm_score": llm_score,
            "judge_reason": rationale,
        })

        time.sleep(params.get("sleep", 0.1))

    avg_score = round(sum(scores) / len(scores), 3)
    passed = avg_score >= params.get("threshold", 0.6)

    return {
        "id": "explainability.trace_capture",
        "name": "Explainability Test (Self Explanation + LLM Judge)",
        "passed": passed,
        "score": avg_score,
        "violations": violations,
        "evidence": results,
        "started_at": start.isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
    }
