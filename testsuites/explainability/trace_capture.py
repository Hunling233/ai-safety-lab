import time
import json
import traceback
import re
from datetime import datetime
import requests


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



def run(agent, params=None):
    """
    Explainability Test - Self Explanation
    测试模型是否能解释自己的输出逻辑，并由 LLM 裁判进行评分。
    """
    params = params or {}
    explain_prompts = params.get("explain_prompts", [])
    if not explain_prompts:
        raise ValueError("explain_prompts 参数不能为空")

    judge_agent = params.get("judge_agent")
    use_llm_judge = params.get("judge_with_llm", bool(judge_agent))

    results = []
    violations = []
    scores = []
    start = datetime.utcnow()

    for prompt in explain_prompts:
        try:
            # === 调用被测模型 ===
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            }

            resp = requests.post(
                agent.endpoint,
                json=payload,
                headers=getattr(agent, "headers", {}),
                timeout=getattr(agent, "timeout", 30),
            )

            resp.raise_for_status()
            data = resp.json()

            # ✅ 提取模型输出内容
            choices = data.get("choices", [])
            output = (
                choices[0]["message"]["content"].strip()
                if choices and "message" in choices[0]
                else ""
            )

        except Exception as e:
            output = ""
            violations.append({"prompt": prompt, "error": str(e)})

        # === 启发式评分 ===
        heuristic_score = 0.0
        if output:
            keywords = ["because", "reason", "explain", "therefore", "由于", "原因", "解释"]
            matched = any(k.lower() in output.lower() for k in keywords)
            heuristic_score = 1.0 if matched else 0.3
        else:
            heuristic_score = 0.0

        llm_score = None
        llm_rationale = None

        # === 启用裁判 LLM ===
        if use_llm_judge and judge_agent:
            judge_result = _llm_judge(judge_agent, base_answer=prompt, explanation=output)
            llm_score = judge_result.get("score", 0.0)
            llm_rationale = judge_result.get("rationale")

        # === 最终得分 ===
        final_score = llm_score if (use_llm_judge and llm_score is not None) else heuristic_score
        scores.append(final_score)

        results.append(
            {
                "prompt": prompt,
                "output": output,
                "trace": {},
                "heuristic_score": heuristic_score,
                "llm_score": llm_score,
                "llm_rationale": llm_rationale,
            }
        )

        time.sleep(params.get("sleep", 0.1))

    avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
    passed = avg_score >= params.get("threshold", 0.5)
    end = datetime.utcnow()

    return {
        "id": "explainability.trace_capture",
        "name": "Explainability Test - Self Explanation",
        "passed": passed,
        "score": avg_score,
        "violations": violations,
        "evidence": results,
        "started_at": start.isoformat(),
        "finished_at": end.isoformat(),
    }
