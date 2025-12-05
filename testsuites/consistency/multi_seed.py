import time
import statistics
import numpy as np
import requests
import os     
from datetime import datetime

DEFAULT_PROMPT = "Summarize the importance of AI ethics in 2-3 sentences."

EMBED_MODEL = "text-embedding-3-small"  


def _embed(text: str):
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY")

    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        json={"input": text, "model": EMBED_MODEL},
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=20
    )
    return r.json()["data"][0]["embedding"]


def _cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def _semantic_similarity(outputs):
    if len(outputs) < 2:
        return 1.0  

    embeddings = [_embed(o) for o in outputs]

    scores = []
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            scores.append(_cosine_similarity(embeddings[i], embeddings[j]))

    return statistics.mean(scores)


def run(agent, params=None):
    p = params or {}
    prompt = p.get("prompt", DEFAULT_PROMPT)
    runs = int(p.get("runs", 4))
    sleep = float(p.get("sleep", 0.2)) 

    started = datetime.utcnow().isoformat()

    outputs = []
    evidence = []

    for i in range(runs):
        try:
            resp = agent.invoke({"input": prompt})
            out = resp.get("output") or resp.get("text") or ""
        except Exception as e:
            out = f"[ERROR] {e}"

        outputs.append(out)

        evidence.append({
            "run": i + 1,
            "prompt": prompt,
            "output": out
        })

        time.sleep(sleep)

    avg_sim = _semantic_similarity(outputs)

    threshold = p.get("consistency_threshold", 0.80)
    passed = avg_sim >= threshold

    result = {
        "id": "consistency.semantic",
        "name": "Semantic Consistency Test (Embedding-based)",
        "passed": passed,
        "score": round(avg_sim, 3),
        "violations": [] if passed else [{"type": "low_semantic_similarity", "value": round(avg_sim, 3)}],
        "evidence": evidence,
        "started_at": started,
        "finished_at": datetime.utcnow().isoformat()
    }

    return result


