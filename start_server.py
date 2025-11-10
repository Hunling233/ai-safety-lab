#!/usr/bin/env python3
"""
启动 AI Safety Lab API 服务器
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["server", "orchestrator", "adapters", "testsuites"]
    )