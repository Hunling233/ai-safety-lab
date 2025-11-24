import time
import numpy as np
from datetime import datetime


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



def run(agent, params=None):
    params = params or {}
    test_sample = params.get("consistency_input", "This is a test sentence for score consistency.")
    repeats = params.get("runs", 5)
    threshold = params.get("threshold", 0.80)

    scores = []
    evidence = []
    start = datetime.utcnow()

    for i in range(repeats):
        resp = agent.invoke({"input": test_sample})
        score = _extract_score(resp)

        evidence.append({
            "run": i + 1,
            "raw_output": resp,
            "parsed_score": score
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

    mean = np.mean(scores)
    std = np.std(scores)
    normalized = max(0, 1 - (std / mean if mean != 0 else 1))

    return {
        "id": "consistency.score_stability",
        "name": "Score Consistency Test",
        "passed": normalized >= threshold,
        "score": round(normalized, 3),
        "mean": round(float(mean), 3),
        "std_dev": round(float(std), 4),
        "variation_coefficient": round(float(std/mean), 4) if mean!=0 else 1,
        "evidence": evidence,
        "started_at": start.isoformat(),
        "finished_at": datetime.utcnow().isoformat()
    }
