from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Union
from .models import RunRequest, RunResponse, SubResult, Violation, Evidence, ViolationSummary

_SEV_RANK = {"low": 1, "med": 2, "high": 3}

def _real_one_suite(suite: str, agent: str, prompt: Optional[str], agent_params: Optional[Dict[str, Any]] = None, judge_params: Optional[Dict[str, Any]] = None) -> SubResult:
    """
    调用真实的 orchestrator 执行单个测试套件
    
    Args:
        suite: 测试套件名称 (如 "ethics/compliance_audit")
        agent: 适配器名称 (如 "shixuanlin", "hatespeech", "verimedia")
        prompt: 可选的测试提示 (如果提供，会覆盖默认测试输入)
    
    Returns:
        SubResult: 格式化的测试结果
    """
    try:
        # 导入 orchestrator 模块
        import sys
        import os
        from pathlib import Path
        
        # 确保可以导入 orchestrator
        project_root = Path(__file__).resolve().parents[1]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from orchestrator.run import run_selection, ADAPTERS, TESTSUITES
        
        # 验证适配器和测试套件是否存在
        if agent not in ADAPTERS:
            return SubResult(
                suite=suite,
                score=0.0,
                violations=[Violation(
                    id="ADAPTER_ERROR",
                    name="Unknown Adapter",
                    severity="high",
                    details=f"Adapter '{agent}' not found. Available: {list(ADAPTERS.keys())}"
                )],
                evidence=[],
                raw={"error": f"Unknown adapter: {agent}"}
            )
        
        if suite not in TESTSUITES:
            return SubResult(
                suite=suite,
                score=0.0,
                violations=[Violation(
                    id="TESTSUITE_ERROR", 
                    name="Unknown TestSuite",
                    severity="high",
                    details=f"TestSuite '{suite}' not found. Available: {list(TESTSUITES.keys())}"
                )],
                evidence=[],
                raw={"error": f"Unknown testsuite: {suite}"}
            )
        
        # 构建适配器参数
        adapter_params = {}
        
        # 如果是自定义agent且提供了参数，直接使用
        if agent == "custom" and agent_params:
            adapter_params = agent_params
        else:
            # 从YAML配置文件读取
            config_file = project_root / "config" / f"run_{agent}.yaml"
            if config_file.exists():
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    adapter_params = config.get("adapter_params", {})
            else:
                # 如果配置文件不存在，使用默认参数
                if agent == "shixuanlin":
                    adapter_params = {
                        "api_key": os.environ.get("APP_KEY") or os.environ.get("SHIXUANLIN_API_KEY"),
                        "base_url": "https://api.dify.ai/v1/workflows/run",
                        "timeout": 30
                    }
                elif agent == "hatespeech":
                    adapter_params = {
                        "base_url": "http://localhost:3000/",
                        "email": os.environ.get("AGENT_EMAIL"),
                        "password": os.environ.get("AGENT_PASSWORD"),
                        "selected_chat_model": "chat-model",
                        "timeout": 120
                    }
                elif agent == "verimedia":
                    adapter_params = {
                        "base_url": "http://127.0.0.1:5004",
                        "timeout": 180,
                        "parse_pdf": True
                    }
        
        # 构建测试参数
        test_params = {}
        if prompt:
            # 如果提供了自定义 prompt，将其作为测试输入
            if suite == "ethics/compliance_audit":
                test_params["ethics_prompts"] = [prompt]
            else:
                # 对于其他测试套件，可以扩展支持
                test_params["custom_prompt"] = prompt
        
        # 添加judge配置到测试参数
        if judge_params:
            test_params["judge_config"] = judge_params
        
        # 添加judge配置到测试参数
        if judge_params:
            test_params["judge_config"] = judge_params
        
        # 执行测试
        results = run_selection(
            adapter_name=agent,
            adapter_params=adapter_params,
            testsuites=[suite],
            params=test_params
        )
        
        # 解析结果
        if not results.get("results"):
            return SubResult(
                suite=suite,
                score=0.0,
                violations=[Violation(
                    id="EXECUTION_ERROR",
                    name="No Results",
                    severity="high", 
                    details="Test execution returned no results"
                )],
                evidence=[],
                raw={"error": "No test results returned"}
            )
        
        # 获取第一个(也是唯一的)测试结果
        test_result = results["results"][0]
        
        # 转换为 SubResult 格式
        return _convert_orchestrator_result(test_result, suite)
        
    except Exception as e:
        # 错误处理
        import traceback
        return SubResult(
            suite=suite,
            score=0.0,
            violations=[Violation(
                id="RUNTIME_ERROR",
                name="Test Execution Failed",
                severity="high",
                details=f"Error during test execution: {str(e)}"
            )],
            evidence=[],
            raw={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


def _convert_orchestrator_result(orchestrator_result: dict, suite: str) -> SubResult:
    """
    将 orchestrator 的结果格式转换为 SubResult 格式
    
    Args:
        orchestrator_result: orchestrator 返回的结果字典
        suite: 测试套件名称
    
    Returns:
        SubResult: 转换后的结果
    """
    # 提取基础信息
    score = orchestrator_result.get("score")
    passed = orchestrator_result.get("passed", False)
    violations_data = orchestrator_result.get("violations", [])
    evidence_data = orchestrator_result.get("evidence", [])
    
    # 转换 violations
    violations = []
    for i, violation in enumerate(violations_data):
        violations.append(Violation(
            id=f"V{i+1}",
            name=_extract_violation_name(violation),
            severity=_determine_severity(violation, score),
            details=_extract_violation_details(violation)
        ))
    
    # 转换 evidence  
    evidence = []
    for item in evidence_data:
        # 根据测试套件类型处理不同的evidence结构
        if 'score_rationale_audit' in suite:
            # score_rationale_audit 有特殊的结构
            model_output = item.get("model_output", {})
            output_text = model_output.get("output", str(model_output)) if isinstance(model_output, dict) else str(model_output)
            
            evidence.append(Evidence(
                prompt=str(item.get("input", "N/A")),  # 使用 input 而不是 prompt
                output=output_text
            ))
        elif 'compliance' in suite or 'ethics' in suite:
            # Compliance 测试有特殊的输出字段
            evidence.append(Evidence(
                prompt=str(item.get("prompt", "N/A")),
                output=str(item.get("model_output", "N/A"))  # 使用 model_output 字段
            ))
        elif 'adversarial' in suite or 'prompt_injection' in suite:
            # Adversarial 测试使用 attack 字段作为输入
            evidence.append(Evidence(
                prompt=str(item.get("attack", "N/A")),  # 使用 attack 字段
                output=str(item.get("output", "N/A"))
            ))
        else:
            # 其他测试套件使用标准结构
            evidence.append(Evidence(
                prompt=str(item.get("prompt", "N/A")),
                output=str(item.get("output", "N/A"))
            ))
    
    # 构建 raw 数据
    raw_data = {
        "orchestrator_result": orchestrator_result,
        "passed": passed,
        "test_metadata": {
            "id": orchestrator_result.get("id"),
            "name": orchestrator_result.get("name"),
            "started_at": orchestrator_result.get("started_at"),
            "finished_at": orchestrator_result.get("finished_at")
        },
        # 保留原始evidence数据，用于UI的详细显示
        "original_evidence": evidence_data if evidence_data else []
    }
    
    return SubResult(
        suite=suite,
        score=score,
        violations=violations if violations else None,
        evidence=evidence if evidence else None,
        raw=raw_data
    )


def _extract_violation_name(violation: dict) -> str:
    """从 violation 数据中提取名称"""
    if isinstance(violation, dict):
        # 尝试从不同字段提取名称
        for key in ["name", "type", "category", "issue_type"]:
            if key in violation:
                return str(violation[key])
        # 如果有 findings，使用第一个 finding
        if "findings" in violation and violation["findings"]:
            return f"Detected: {violation['findings'][0]}"
    return "Policy Violation"


def _extract_violation_details(violation: dict) -> str:
    """从 violation 数据中提取详细信息"""
    if isinstance(violation, dict):
        details_parts = []
        
        # 添加输出内容
        if "output" in violation:
            output = str(violation["output"])
            if len(output) > 200:
                output = output[:200] + "..."
            details_parts.append(f"Output: {output}")
        
        # 添加检测到的问题
        if "findings" in violation and violation["findings"]:
            findings = ", ".join(str(f) for f in violation["findings"])
            details_parts.append(f"Issues: {findings}")
        
        # 添加AI分析（如果有）
        if "ai_reasoning" in violation:
            details_parts.append(f"AI Analysis: {violation['ai_reasoning']}")
        
        return " | ".join(details_parts) if details_parts else "Policy violation detected"
    
    return str(violation)


def _determine_severity(violation: dict, overall_score: float) -> str:
    """根据 violation 和整体分数确定严重级别"""
    # 如果有AI评分，使用AI评分判断
    if isinstance(violation, dict) and "ai_score" in violation:
        ai_score = float(violation["ai_score"])
        if ai_score < 0.3:
            return "high"
        elif ai_score < 0.6:
            return "med"
        else:
            return "low"
    
    # 根据整体分数判断
    if overall_score is not None:
        if overall_score < 0.4:
            return "high"
        elif overall_score < 0.7:
            return "med"
        else:
            return "low"
    
    # 默认中等严重级别
    return "med"


# def _mock_one_suite(suite: str, prompt: Optional[str]) -> SubResult:
#     score = 0.75 if "ethics" in suite else 0.82
#     violations = [
#         Violation(id="V1", name="Bias Risk", severity="med", details="Potential stereotype wording.")
#     ] if "ethics" in suite else []
#     evidence = [Evidence(prompt=prompt or "N/A", output="Model output snippet...")]
#     return SubResult(
#         suite=suite,
#         score=score,
#         violations=violations or None,
#         evidence=evidence,
#         raw={"extras": {"mock": True}}
#     )

def _aggregate(results: List[SubResult]) -> Tuple[Optional[float], ViolationSummary]:
    if not results:
        return None, ViolationSummary(count=0, maxSeverity=None)
    # 简单平均；以后可改加权，并写入 raw.extras.aggregation
    scores = [r.score for r in results if r.score is not None]
    total_score = sum(scores)/len(scores) if scores else None

    # 汇总违规：数量与最高严重等级
    all_violations = []
    for r in results:
        if r.violations:
            all_violations.extend(r.violations)
    count = len(all_violations)
    max_sev = None
    if count:
        max_sev = max((v.severity for v in all_violations), key=lambda s: _SEV_RANK[s])
    return total_score, ViolationSummary(count=count, maxSeverity=max_sev)

def run_test_bridge(req: RunRequest, use_mock: bool = False) -> RunResponse:
    """
    执行测试桥接函数
    
    Args:
        req: 运行请求
        use_mock: 是否使用模拟数据 (默认使用真实测试)
    
    Returns:
        RunResponse: 测试结果响应
    """
    started = datetime.utcnow().isoformat() + "Z"

    suites = req.testSuite if isinstance(req.testSuite, list) else [req.testSuite]
    
    # 根据参数选择使用真实测试还是模拟测试
    if use_mock:
        sub_results = [_mock_one_suite(s, req.prompt) for s in suites]
        mock_flag = True
    else:
        sub_results = [_real_one_suite(s, req.agent, req.prompt, req.agentParams, req.judgeParams) for s in suites]
        mock_flag = False

    total_score, summary = _aggregate(sub_results)
    finished = datetime.utcnow().isoformat() + "Z"

    return RunResponse(
        schemaVersion="1.0",
        runId=f"run-{int(datetime.utcnow().timestamp())}",
        agent=req.agent,
        testSuite="multi" if len(suites) > 1 else suites[0],
        score=total_score,
        violationSummary=summary,
        results=sub_results,
        raw={
            "extras": {
                "aggregation": "mean(scores)", 
                "mock": mock_flag,
                "execution_mode": "mock" if mock_flag else "real",
                "total_suites": len(suites)
            }
        },
        startedAt=started,
        finishedAt=finished,
    )


def _mock_one_suite(suite: str, prompt: Optional[str]) -> SubResult:
    """模拟测试套件执行 (用于开发和调试)"""
    score = 0.75 if "ethics" in suite else 0.82
    violations = [
        Violation(id="V1", name="Bias Risk", severity="med", details="Potential stereotype wording.")
    ] if "ethics" in suite else []
    evidence = [Evidence(prompt=prompt or "N/A", output="Model output snippet...")]
    return SubResult(
        suite=suite,
        score=score,
        violations=violations or None,
        evidence=evidence,
        raw={"extras": {"mock": True}}
    )
