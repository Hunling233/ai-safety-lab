from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Callable, Optional

import yaml

# Ensure project root is on sys.path when running this file directly (python orchestrator/run.py)
if __package__ is None or __package__ == "":
    _project_root = Path(__file__).resolve().parents[1]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

from adapters.verimedia_adapter import VeriMediaAdapter
from adapters.http_agent import HTTPAgent

# ---- Defaults -------------------------------------------------------------
DEFAULT_ADAPTER = "verimedia"
DEFAULT_TESTSUITES = ["ethics/compliance_audit"]

# ---- Adapter registry -----------------------------------------------------
ADAPTERS: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "verimedia": lambda params: VeriMediaAdapter(
        base_url=params.get("base_url", "http://127.0.0.1:5004"),
        timeout=int(params.get("timeout", 120)),
        parse_pdf=bool(params.get("parse_pdf", True)),
    ),
    "http": lambda params: HTTPAgent(
        endpoint=params.get("endpoint", "http://127.0.0.1:8000/invoke"),
        headers=params.get("headers"),
        timeout=int(params.get("timeout", 30)),
    ),
}


# ---- Testsuite registry ---------------------------------------------------
def _ts_ethics_compliance_audit():
    from testsuites.ethics.compliance_audit import run as _run
    return _run


TESTSUITES: Dict[str, Callable[[], Callable[..., Dict[str, Any]]]] = {
    "ethics/compliance_audit": _ts_ethics_compliance_audit,
}


# ---- Orchestrator core ----------------------------------------------------
def load_config(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping")
    return data


def build_adapter(name: str, params: Optional[Dict[str, Any]] = None):
    params = params or {}
    if name not in ADAPTERS:
        raise KeyError(f"Unknown adapter: {name}")
    return ADAPTERS[name](params)


def run_from_config(config_path: str) -> Dict[str, Any]:
    cfg_file = Path(config_path)
    cfg = load_config(cfg_file)

    adapter_name: str = cfg.get("adapter") or DEFAULT_ADAPTER
    adapter_params: Dict[str, Any] = cfg.get("adapter_params", {})
    testsuites = cfg.get("testsuites") or DEFAULT_TESTSUITES
    samples = cfg.get("samples", [])
    output_dir = Path(cfg.get("output_dir", "runs/latest"))
    output_dir.mkdir(parents=True, exist_ok=True)

    adapter = build_adapter(adapter_name, adapter_params)

    all_results = {"adapter": adapter_name, "results": []}

    for ts in testsuites:
        if ts not in TESTSUITES:
            raise KeyError(f"Unknown testsuite: {ts}")
        ts_run = TESTSUITES[ts]()

        # 统一按文本型 testsuite 调用：
        # - 对于 VeriMediaAdapter，已在适配器内部实现 invoke(prompt)（将文本写临时文件分析）
        res = ts_run(adapter, params=cfg)
        all_results["results"].append({"testsuite": ts, **res})

    # 写出汇总 JSON
    (output_dir / "summary.json").write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return all_results


def run_selection(
    adapter_name: str = DEFAULT_ADAPTER,
    adapter_params: Optional[Dict[str, Any]] = None,
    testsuites: Optional[list[str]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    以编程方式运行：选择适配器与测试集（带默认），并传入 params 给 testsuite。
    """
    adapter_params = adapter_params or {}
    testsuites = testsuites or DEFAULT_TESTSUITES
    params = params or {}

    adapter = build_adapter(adapter_name, adapter_params)

    all_results = {"adapter": adapter_name, "results": []}
    for ts in testsuites:
        if ts not in TESTSUITES:
            raise KeyError(f"Unknown testsuite: {ts}")
        ts_run = TESTSUITES[ts]()
        res = ts_run(adapter, params=params)
        all_results["results"].append({"testsuite": ts, **res})
    return all_results


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        summary = run_from_config(sys.argv[1])
    else:
        # 无配置时使用默认：adapter=verimedia, testsuite=ethics/compliance_audit
        print("[orchestrator] No config provided. Running defaults: adapter=verimedia, testsuite=ethics/compliance_audit")
        summary = run_selection()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
