# testsuites/adversarial/graph_attack_agent.py
import os
import time
import traceback
import requests

# 你的实现（稍作改造以便导入）
from graph_tiger.graphs import graph_loader
from graph_tiger.attacks import Attack
import matplotlib.pyplot as plt


class GraphAttackAgent:
    def __init__(self, output_dir="./plots"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run_attack_experiments(
        self,
        graph_type="ky2",
        attack_scope="node",
        runs=10,
        steps=30,
        seed=1,
        include_visual=False
    ):
        graph = graph_loader(graph_type=graph_type, seed=seed)

        base_params = {
            "runs": 1,
            "steps": steps,
            "seed": seed,
            "plot_transition": include_visual,
            "gif_animation": include_visual,
            "gif_snaps": include_visual,
            "edge_style": None,
            "node_style": None,
            "fa_iter": 20
        }

        if attack_scope == "node":
            attacks = ['rnd_node', 'id_node', 'rd_node', 'ib_node', 'rb_node']
        else:
            attacks = ['rnd_edge', 'id_edge', 'rd_edge', 'ib_edge', 'rb_edge']

        results = {}
        for attack in attacks:
            params = base_params.copy()
            params["attack"] = attack
            if 'rb' in attack or 'ib' in attack:
                params["attack_approx"] = int(0.1 * len(graph))
            else:
                params["attack_approx"] = None

            atk = Attack(graph, **params)
            sim_result = atk.run_simulation()
            # 兼容返回：若是 dict 且包含 lcc 字段则取之；若是 list/tuple 则当作 lcc 列表
            if isinstance(sim_result, dict) and "lcc" in sim_result:
                lcc = sim_result["lcc"]
            elif isinstance(sim_result, (list, tuple)):
                lcc = list(sim_result)
            else:
                # 最保守处理：尝试把可迭代元素转成 list，否则将 raw 文本放入 evidence
                try:
                    lcc = list(sim_result)
                except Exception:
                    lcc = None

            results[attack] = {
                "raw": sim_result,
                "lcc": lcc
            }

        return {
            "graph_type": graph_type,
            "attack_scope": attack_scope,
            "steps": steps,
            "results": results
        }

    def plot_results(self, graph, results_data, title="graph_attack_results"):
        steps = results_data["steps"]
        results = results_data["results"]

        plt.figure(figsize=(6.4, 4.8))
        for method, payload in results.items():
            result = payload.get("lcc")
            if not result:
                continue
            # 如果 lcc 是 absolute node counts，做归一化（除以 graph size）
            try:
                result_norm = [r / len(graph) for r in result]
            except Exception:
                result_norm = result
            plt.plot(list(range(steps)), result_norm, label=method)

        plt.ylim(0, 1)
        plt.ylabel("LCC (Normalized)")
        plt.xlabel("Removed Ratio / Steps")
        plt.title(title)
        plt.legend()
        output_path = os.path.join(self.output_dir, f"{title}.pdf")
        plt.savefig(output_path)
        plt.close()
        return output_path


def run(agent, params=None):
    """
    orchestrator-compatible entrypoint
    params 可接收：
      - graph_type, attack_scope, runs, steps, seed, include_visual, output_dir
    """
    started_at = time.time()
    params = params or {}

    graph_type = params.get("graph_type", "ky2")
    attack_scope = params.get("attack_scope", "node")
    runs = params.get("graph_runs", 1)
    steps = params.get("graph_steps", 30)
    seed = params.get("graph_seed", 1)
    include_visual = params.get("include_visual", False)
    output_dir = params.get("output_dir", "./plots")

    agent_endpoint = None
    if hasattr(agent, "endpoint"):
        agent_endpoint = getattr(agent, "endpoint")
    elif isinstance(agent, dict):
        agent_endpoint = agent.get("endpoint")

    gagent = GraphAttackAgent(output_dir=output_dir)

    try:
        results = gagent.run_attack_experiments(
            graph_type=graph_type,
            attack_scope=attack_scope,
            runs=runs,
            steps=steps,
            seed=seed,
            include_visual=include_visual
        )

        # 可选：画图（如果需要且 graph 数据可用）
        # graph = graph_loader(graph_type=graph_type, seed=seed)
        # plot_path = gagent.plot_results(graph, results, title=f"attack_{graph_type}_{attack_scope}")

        # 简单连通性检测：ping agent endpoint（如果提供）
        agent_status = None
        agent_example_response = None
        if agent_endpoint:
            try:
                # 优先按常见字段尝试
                r = requests.post(agent_endpoint, json={"input": "ping"}, timeout=5)
                try:
                    agent_example_response = r.json()
                except Exception:
                    agent_example_response = r.text
                agent_status = {"ok": r.status_code == 200, "status_code": r.status_code}
            except Exception as e:
                agent_status = {"ok": False, "error": str(e)}

        finished_at = time.time()
        # 评分：使用所有攻击的平均“final LCC 衰减”作为 damage，然后 score = 1 - avg_damage
        damages = []
        for k, v in results["results"].items():
            lcc = v.get("lcc")
            if lcc and isinstance(lcc, (list, tuple)) and len(lcc) > 0:
                final = float(lcc[-1])
                # 归一化假设：如果 final 在 0..1 之间则直接使用，否则尝试按节点数归一化（保守）
                if 0.0 <= final <= 1.0:
                    norm_final = final
                else:
                    try:
                        # 暂用 graph length as denominator
                        graph = graph_loader(graph_type=graph_type, seed=seed)
                        norm_final = final / max(1, len(graph))
                    except Exception:
                        norm_final = min(1.0, max(0.0, final))
                damages.append(1.0 - norm_final)
            else:
                # 无数据视为最坏（已被破坏）
                damages.append(1.0)

        avg_damage = sum(damages) / max(1, len(damages))
        score = round(max(0.0, min(1.0, 1.0 - avg_damage)), 3)
        passed = score >= 0.7

        evidence = {
            "graph_attack_results": results,
            "agent_check": {"endpoint": agent_endpoint, "status": agent_status, "example_response": agent_example_response}
        }

        return {
            "id": "adversarial.graph_attack_agent",
            "name": "Graph Attack Agent - Network Robustness",
            "passed": passed,
            "score": score,
            "violations": [],
            "evidence": evidence,
            "started_at": started_at,
            "finished_at": finished_at
        }

    except Exception as e:
        return {
            "id": "adversarial.graph_attack_agent",
            "name": "Graph Attack Agent - Network Robustness",
            "passed": False,
            "score": 0.0,
            "violations": [],
            "evidence": [{"error": str(e), "trace": traceback.format_exc()}],
            "started_at": started_at,
            "finished_at": time.time()
        }
