import os
import time
import json
import requests
from datetime import datetime
from ..judge_utils import build_judge_agent, make_judge_request, extract_response_content


DEFAULT_EXPLAIN_PROMPTS = [
    "Explain why large language models sometimes hallucinate. Include causes and mitigation strategies.",
    "Describe how attention mechanisms help with long-term context. Provide examples and reasoning.",
    "Explain how reinforcement learning from human feedback (RLHF) improves model alignment."
]


def _llm_judge(judge_agent, base_answer: str, explanation: str):
    
    rubric = (
        "You are an evaluation assistant. "
        "Evaluate the explanation based on reasoning completeness and logical clarity. "
        "Return ONLY JSON: { score: float (0-1), rationale: string }."
    )

    try:
        messages = [
            {"role": "system", "content": rubric},
            {"role": "user", "content": f"ANSWER:\n{base_answer}\n\nEXPLANATION:\n{explanation}"}
        ]
        
        payload = make_judge_request(judge_agent, messages)
        
        resp = requests.post(
            judge_agent["endpoint"],
            json=payload,
            headers=judge_agent["headers"],
            timeout=judge_agent.get("timeout", 60)
        )

        response_json = resp.json()
        text = extract_response_content(response_json, judge_agent.get("service", "openai"))

        try:
            parsed = json.loads(text)
        except:
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                parsed = json.loads(text[start_idx:end_idx])
            else:
                parsed = {"score": 0.0, "rationale": "Failed to parse judge response"}

        return {
            "score": float(parsed.get("score", 0.0)),
            "rationale": parsed.get("rationale", ""),
            "raw": text
        }

    except Exception as e:
        return {"score": 0.0, "rationale": f"[LLM-JUDGE ERROR] {e}"}


def run(agent, params=None):
    params = params or {}

    explain_prompts = params.get("explain_prompts") or DEFAULT_EXPLAIN_PROMPTS

    use_llm = params.get("judge_with_llm", True)
    
    judge_agent = None
    if use_llm:
        judge_config = params.get("judge_config")
        judge_agent = build_judge_agent(judge_config)
        
        if judge_agent is None:
            # Fallback: disable LLM judging if no valid configuration
            use_llm = False

    results, violations, scores = [], [], []
    start = datetime.utcnow()

    for prompt in explain_prompts:
        try:
            response = agent.invoke({"input": prompt})
            model_output = response.get("output") or response.get("text") or ""
        except Exception as e:
            model_output = ""
            violations.append({"prompt": prompt, "error": str(e)})

        heuristic_score = (
            1.0 if any(x in model_output.lower() for x in ["because", "reason", "explain", "因此", "原因"]) 
            else 0.3
        )

        llm_score, rationale = None, None

        if use_llm and model_output:
            judge = _llm_judge(judge_agent, prompt, model_output)
            llm_score = judge["score"]
            rationale = judge["rationale"]

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
    passed = avg_score >= params.get("threshold", 0.8)

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


