from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import RunRequest, RunResponse
from .adapters_bridge import run_test_bridge

app = FastAPI(title="UNICC API", version="0.1")

# 开发期先放开 CORS，后续再收紧
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/agents")
def get_agents():
    """获取可用的AI代理列表"""
    return {
        "agents": [
            {
                "id": "openai",
                "name": "OpenAI GPT",
                "description": "OpenAI的GPT系列模型",
                "type": "llm"
            },
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "description": "Anthropic的Claude系列模型", 
                "type": "llm"
            },
            {
                "id": "langchain",
                "name": "LangChain Agent",
                "description": "基于LangChain的智能代理",
                "type": "agent"
            },
            {
                "id": "custom",
                "name": "Custom Agent",
                "description": "用户自定义的AI代理",
                "type": "custom"
            },
            {
                "id": "mock",
                "name": "Mock Agent",
                "description": "用于测试的模拟代理",
                "type": "mock"
            }
        ]
    }

@app.post("/api/run", response_model=RunResponse)
def run_api(req: RunRequest, mock: bool = False):
    """
    执行AI安全测试
    
    Args:
        req: 测试请求 (包含agent, testSuite, prompt等)
        mock: 是否使用模拟数据 (默认false，使用真实测试)
    
    Returns:
        RunResponse: 测试结果
    """
    return run_test_bridge(req, use_mock=mock)

@app.post("/api/run/mock", response_model=RunResponse) 
def run_mock_api(req: RunRequest):
    """
    执行模拟测试 (用于开发和调试)
    """
    return run_test_bridge(req, use_mock=True)

@app.post("/api/run/real", response_model=RunResponse)
def run_real_api(req: RunRequest):
    """
    执行真实测试 (调用实际的 orchestrator)
    """
    return run_test_bridge(req, use_mock=False)
