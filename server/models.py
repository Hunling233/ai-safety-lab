from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field

# 入参：支持单个或多个 testSuite
class RunRequest(BaseModel):
    agent: str
    testSuite: Union[str, List[str]]
    prompt: Optional[str] = None
    agentParams: Optional[dict] = None
    judgeParams: Optional[dict] = None

# 顶层可选的总览统计
class Violation(BaseModel):
    id: str
    name: str
    severity: Literal["low", "med", "high"]
    details: str

class Evidence(BaseModel):
    prompt: str
    output: str

class ViolationSummary(BaseModel):
    count: int = 0
    maxSeverity: Optional[Literal["low", "med", "high"]] = None

# 子结果（单个测试的独立报告）
class SubResult(BaseModel):
    suite: str
    score: Optional[float] = None
    violations: Optional[List[Violation]] = None
    evidence: Optional[List[Evidence]] = None
    raw: Optional[dict] = None  # 放 extras 等

# 返回体（顶层 + 子结果）
class RunResponse(BaseModel):
    schemaVersion: str = "1.0"
    runId: str
    agent: str
    testSuite: str = Field(default="multi")  # 兼容顶层字段；多测时给"multi"
    score: Optional[float] = None
    violationSummary: Optional[ViolationSummary] = None
    results: Optional[List[SubResult]] = None
    raw: Optional[dict] = None
    startedAt: str
    finishedAt: str
