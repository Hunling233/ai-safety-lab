from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Callable, Optional

import yaml

# Ensure project root is on sys.path when running this file directly (python orchestrator/run.py)
if __package__ is None or __package__ == "":
    _project_root = Path(__file__).resolve().parents[1]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

# Load OpenAI API key from config if not already set
def load_openai_config():
    """Load OpenAI configuration from config/openai.env if API key is not already set."""
    if not os.getenv('OPENAI_API_KEY'):
        config_path = Path(__file__).resolve().parents[1] / 'config' / 'openai.env'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            if key and value:
                                os.environ[key] = value
                print(f"[config] Loaded OpenAI configuration from {config_path}")
            except Exception as e:
                print(f"[warning] Failed to load config from {config_path}: {e}")
        else:
            print(f"[warning] OpenAI config file not found at {config_path}")

# Load configuration before importing adapters
load_openai_config()

from adapters.verimedia_adapter import VeriMediaAdapter
from adapters.http_agent import HTTPAgent
from adapters.hatespeech_adapter import HateSpeechAdapter
from adapters.shixuanlin_adapter import ShixuanlinAdapter
from adapters.universal_http_agent import UniversalHTTPAgent

def _create_langchain_adapter(params):
    """Create LangChain adapter from parameters"""
    try:
        from adapters.langchain_adapter import create_langchain_adapter
        
        # Get the LangChain object from params
        langchain_object = params.get("langchain_object")
        if langchain_object is None:
            raise ValueError("LangChain adapter requires 'langchain_object' parameter")
        
        input_key = params.get("input_key", "input")
        output_key = params.get("output_key", "output")
        
        return create_langchain_adapter(
            langchain_object, 
            input_key=input_key, 
            output_key=output_key
        )
    except ImportError:
        raise ImportError("LangChain is not installed. Please install with: pip install langchain")
    except Exception as e:
        raise ValueError(f"Failed to create LangChain adapter: {str(e)}")

# ---- Defaults -------------------------------------------------------------
DEFAULT_ADAPTER = "verimedia"
DEFAULT_TESTSUITES = [
    "ethics/compliance_audit",
    "adversarial/prompt_injection", 
    "consistency/multi_seed",
    "consistency/score_consistency",
    "explainability/trace_capture",
    "explainability/score_rationale_audit"
]

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
    "hatespeech": lambda params: HateSpeechAdapter(
        base_url=params.get("base_url", "http://localhost:3000"),
        email=params.get("email"),
        password=params.get("password"),
        selected_chat_model=params.get("selected_chat_model", "chat-model"),
        default_file_path=params.get("file_path"),
        timeout=int(params.get("timeout", 120)),
    ),
    "shixuanlin": lambda params: ShixuanlinAdapter(
        api_key=params.get("api_key"),
        base_url=params.get("base_url", "https://api.dify.ai/v1/workflows/run"),
        timeout=int(params.get("timeout", 30)),
    ),
    "custom": lambda params: UniversalHTTPAgent(
        endpoint=params.get("endpoint"),
        api_key=params.get("api_key"),
        api_format=params.get("format", "openai_compatible"),
        model_name=params.get("model"),
        timeout=int(params.get("timeout", 30)),
    ),
    "langchain": lambda params: _create_langchain_adapter(params),
}


# ---- Testsuite registry ---------------------------------------------------
def _ts_ethics_compliance_audit():
    from testsuites.ethics.compliance_audit import run as _run
    return _run


def _ts_adversarial_prompt_injection():
    from testsuites.adversarial.prompt_injection import run as _run
    return _run


def _ts_consistency_multi_seed():
    from testsuites.consistency.multi_seed import run as _run
    return _run


def _ts_explainability_trace_capture():
    from testsuites.explainability.trace_capture import run as _run
    return _run


def _ts_consistency_score_consistency():
    from testsuites.consistency.score_consistency import run as _run
    return _run


def _ts_explainability_score_rationale_audit():
    from testsuites.explainability.score_rationale_audit import run as _run
    return _run


TESTSUITES: Dict[str, Callable[[], Callable[..., Dict[str, Any]]]] = {
    "ethics/compliance_audit": _ts_ethics_compliance_audit,
    "adversarial/prompt_injection": _ts_adversarial_prompt_injection,
    "consistency/multi_seed": _ts_consistency_multi_seed,
    "consistency/score_consistency": _ts_consistency_score_consistency,
    "explainability/trace_capture": _ts_explainability_trace_capture,
    "explainability/score_rationale_audit": _ts_explainability_score_rationale_audit,
}


# ---- Orchestrator core ----------------------------------------------------
def _save_text_outputs(ts_key: str, evidence: list[dict], out_dir: Path) -> None:
    target = Path("runs") / "artifacts"
    target.mkdir(parents=True, exist_ok=True)
    safe_ts = ts_key.replace("/", "_")
    for i, item in enumerate(evidence or [], start=1):
        text = str(item.get("output", ""))
        ms = int(time.time() * 1000)
        fname = f"{safe_ts}-{i}-{ms}.txt"
        (target / fname).write_text(text, encoding="utf-8")


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

        # 可选：落盘每条回答文本到 output_dir/outputs/
        save_flag = cfg.get("save_outputs") or (cfg.get("reporting", {}) or {}).get("save_outputs")
        if save_flag:
            _save_text_outputs(ts, res.get("evidence") or [], output_dir)

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
        # 若通过 params 控制保存输出
        save_flag = (params or {}).get("save_outputs") or ((params or {}).get("reporting", {}) or {}).get("save_outputs")
        out_dir = Path((params or {}).get("output_dir", "runs/latest"))
        if save_flag:
            _save_text_outputs(ts, res.get("evidence") or [], out_dir)
    return all_results


if __name__ == "__main__":
    if len(sys.argv) == 3:
        # 两个参数模式：测试项目 + Agent配置文件
        testsuite_name = sys.argv[1]
        agent_config_path = sys.argv[2]
        
        # 验证测试套件是否存在
        if testsuite_name not in TESTSUITES:
            print(f"❌ 未知的测试套件: {testsuite_name}")
            print(f"可用的测试套件: {list(TESTSUITES.keys())}")
            sys.exit(1)
        
        # 加载Agent配置
        cfg_file = Path(agent_config_path)
        cfg = load_config(cfg_file)
        
        adapter_name: str = cfg.get("adapter") or DEFAULT_ADAPTER
        adapter_params: Dict[str, Any] = cfg.get("adapter_params", {})
        output_dir = Path(cfg.get("output_dir", f"runs/{testsuite_name.replace('/', '_')}"))
        
        print(f"[orchestrator] 运行测试套件: {testsuite_name}")
        print(f"[orchestrator] 使用Agent配置: {agent_config_path}")
        print(f"[orchestrator] Adapter: {adapter_name}")
        
        # 运行指定的测试套件
        summary = run_selection(
            adapter_name=adapter_name,
            adapter_params=adapter_params,
            testsuites=[testsuite_name],
            params=cfg
        )
    elif len(sys.argv) == 2:
        # 单个参数模式：完整配置文件（原有逻辑）
        summary = run_from_config(sys.argv[1])
    else:
        # 无参数：使用默认设置
        print("[orchestrator] No config provided. Running defaults: adapter=verimedia, testsuite=ethics/compliance_audit")
        summary = run_selection()
    
    print(json.dumps(summary, ensure_ascii=False, indent=2))
